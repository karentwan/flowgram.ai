"""Task lifecycle manager — mirrors Node's WorkflowApplication.

Holds an in-memory task map (task_id → Task). ``run`` starts a task in the
background and returns immediately; ``result`` returns outputs once terminated;
``report`` returns the current state; ``cancel`` requests termination.

Resume-on-crash: when a MySQL checkpointer is configured (DATABASE_URL set +
langgraph-checkpoint-mysql installed), each task's State is persisted per step
keyed by task_id. ``resume(task_id)`` rebuilds the graph and continues from the
last checkpoint after a process restart. If the DB/checkpointer is unavailable,
runs proceed in-memory only (no resume capability).
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.core.observability import ObservabilityRecorder, create_task_run_record
from app.engine.checkpointer import get_checkpointer
from app.engine.graph import build_graph
from app.engine.state import (
    NODE_STATUS_KEY,
    OUTPUTS_KEY,
    WORKFLOW_STATUS_KEY,
    get_outputs,
    get_workflow_status,
    is_terminated,
    new_state,
    set_workflow_status,
)
from app.nodes.base import register_recorder, unregister_recorder

_log = get_logger(__name__)


@dataclass
class Task:
    """A running (or finished) workflow execution. Mirrors Node's ITask."""

    id: str
    inputs: dict[str, Any]
    state: dict[str, Any]
    future: asyncio.Task[Any] | None = None
    error: str | None = None

    @property
    def terminated(self) -> bool:
        return is_terminated(self.state)

    @property
    def outputs(self) -> dict[str, Any]:
        return get_outputs(self.state)

    def cancel(self) -> bool:
        # If the task already reached a terminal state, don't overwrite it
        # (avoids a late cancel clobbering a succeeded/failed result).
        if self.terminated:
            return True
        if self.future is not None and not self.future.done():
            self.future.cancel()
            set_workflow_status(self.state, "canceled")
            return True
        set_workflow_status(self.state, "canceled")
        return True


class TaskManager:
    """In-memory task registry + execution. Singleton (mirrors WorkflowApplication.instance)."""

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def run(self, schema: dict[str, Any], inputs: dict[str, Any]) -> str:
        """Build the graph and start execution in the background. Returns task_id.

        Must be called within a running event loop (the ASGI server provides one;
        tests use pytest-asyncio). The task is scheduled as a fire-and-forget
        background coroutine on the current loop. Graph construction + checkpointer
        acquisition happen inside _execute (async) so the MySQL checkpointer can
        be awaited.
        """
        task_id = "task_" + secrets.token_hex(12)
        state = new_state(task_id, inputs)
        task = Task(id=task_id, inputs=inputs, state=state)
        task.schema = schema  # type: ignore[attr-defined]
        self.tasks[task_id] = task

        # Observability: open a DB session for the task's duration and register
        # a recorder so node fns can record events. If the DB is unavailable,
        # recorder.session is None and observations degrade to log-only.
        session = self._try_open_session()
        create_task_run_record(session, task_id, inputs)
        recorder = ObservabilityRecorder(session, task_id)
        register_recorder(task_id, recorder)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as e:
            raise RuntimeError(
                "TaskManager.run() must be called within a running event loop "
                "(the ASGI server provides one)."
            ) from e
        task.future = loop.create_task(self._execute(task, recorder, session))
        _log.info("task started", task_id=task_id)
        return task_id

    def _try_open_session(self):
        """Open a DB session if configured; return None if DB is unavailable."""
        try:
            from app.core.database import get_session_factory

            return get_session_factory()()
        except Exception as e:
            _log.warning("db session unavailable, observability degraded", error=str(e))
            return None

    async def _execute(self, task: Task, recorder, session) -> None:
        """Run the graph to completion, updating task.state + recording stats.

        Graph is built here (not in run()) so the MySQL checkpointer can be
        awaited. If a checkpointer is available, the graph persists State per
        step keyed by task_id — enabling resume-on-crash (re-invoking with the
        same thread_id continues from the last checkpoint).
        """
        try:
            checkpointer = await get_checkpointer()
            _log.info(
                "checkpointer acquired",
                task_id=task.id,
                mode="mysql" if checkpointer is not None else "memory",
            )
            graph = build_graph(task.schema, checkpointer=checkpointer)  # type: ignore[attr-defined]
            # thread_id = task_id so checkpoint chains are per-task.
            config = {"configurable": {"thread_id": task.id}} if checkpointer else None
            _log.info(
                "graph invoke start",
                task_id=task.id,
                thread_id=task.id,
                has_config=config is not None,
            )
            try:
                final_state = await graph.ainvoke(task.state, config=config)
            except Exception as e:
                _log.error(
                    "graph invoke failed",
                    task_id=task.id,
                    error=str(e),
                    exc_info=True,
                )
                raise
            _log.info("graph invoke done", task_id=task.id)
            if isinstance(final_state, dict):
                task.state.update(final_state)
            if not is_terminated(task.state):
                set_workflow_status(task.state, "succeeded")
            _log.info(
                "task finished",
                task_id=task.id,
                status=get_workflow_status(task.state),
            )
            recorder.finish_task(
                status=get_workflow_status(task.state),
                outputs=task.outputs,
                state_snapshot=dict(task.state),
                total_usage={},
            )
        except asyncio.CancelledError:
            set_workflow_status(task.state, "canceled")
            recorder.finish_task(
                status="canceled", outputs=None, state_snapshot=None, total_usage=None
            )
            _log.info("task canceled", task_id=task.id)
            raise
        except Exception as e:
            task.error = str(e)
            set_workflow_status(task.state, "failed")
            recorder.finish_task(
                status="failed",
                outputs=None,
                state_snapshot=None,
                total_usage=None,
                error=str(e),
            )
            _log.error(
                "task failed",
                task_id=task.id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
        finally:
            unregister_recorder(task.id)
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

    async def resume(self, task_id: str) -> str | None:
        """Resume an interrupted/crashed task from its last checkpoint.

        Rebuilds the graph with the same checkpointer + thread_id and re-invokes;
        LangGraph picks up from the persisted checkpoint rather than restarting.
        Returns the task_id if a checkpoint exists, else None.
        """
        task = self.tasks.get(task_id)
        if task is None:
            return None
        checkpointer = await get_checkpointer()
        if checkpointer is None:
            _log.warning("cannot resume: no checkpointer available", task_id=task_id)
            return None
        _log.info("resume: checkpointer acquired", task_id=task_id, mode="mysql")
        graph = build_graph(task.schema, checkpointer=checkpointer)  # type: ignore[attr-defined]
        loop = asyncio.get_running_loop()
        task.future = loop.create_task(self._resume_invoke(task, graph))
        _log.info("task resuming from checkpoint", task_id=task_id)
        return task_id

    async def _resume_invoke(self, task: Task, graph) -> None:
        """Invoke a graph to resume from checkpoint (passes None input)."""
        try:
            config = {"configurable": {"thread_id": task.id}}
            final_state = await graph.ainvoke(None, config=config)
            if isinstance(final_state, dict):
                task.state.update(final_state)
            if not is_terminated(task.state):
                set_workflow_status(task.state, "succeeded")
            _log.info("task resumed+finished", task_id=task.id, status=get_workflow_status(task.state))
        except Exception as e:
            task.error = str(e)
            set_workflow_status(task.state, "failed")
            _log.error(
                "task resume failed",
                task_id=task.id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

    def result(self, task_id: str) -> dict[str, Any] | None:
        """Return outputs if the task terminated, else None (mirrors Node result())."""
        task = self.tasks.get(task_id)
        if task is None:
            return None
        if not task.terminated:
            return None
        return task.outputs if get_workflow_status(task.state) == "succeeded" else task.outputs

    def report(self, task_id: str) -> dict[str, Any] | None:
        """Return a report dict (mirrors Node IReport shape + observability stats)."""
        task = self.tasks.get(task_id)
        if task is None:
            return None
        node_status = task.state.get(NODE_STATUS_KEY, {})
        # Pull observability stats from the DB if available.
        stats = self._query_stats(task_id)
        wf_status = get_workflow_status(task.state)
        # Group snapshots by nodeID so the editor can render each node's
        # results under it. Mirrors Node's NodeReport.snapshots structure.
        from app.engine.state import SNAPSHOTS_KEY

        all_snapshots = task.state.get(SNAPSHOTS_KEY, [])
        snaps_by_node: dict[str, list[dict[str, Any]]] = {}
        for snap in all_snapshots:
            snaps_by_node.setdefault(snap.get("nodeID", ""), []).append(snap)

        # Build reports: every node with a status gets a snapshots array (empty
        # if none) — the editor reads nodeReport.snapshots.length unconditionally.
        reports: dict[str, Any] = {}
        for node_id, status in node_status.items():
            reports[node_id] = {
                "id": node_id,
                "status": status,
                "snapshots": snaps_by_node.get(node_id, []),
            }
        return {
            "id": task.id,
            "inputs": task.inputs,
            "outputs": task.outputs,
            # workflowStatus MUST include `terminated` (boolean) — the editor's
            # runtime plugin polls report and stops on workflowStatus.terminated
            # being true. Mirrors Node's StatusData {status, terminated}.
            "workflowStatus": {"status": wf_status, "terminated": wf_status in {"succeeded", "failed", "canceled"}},
            "reports": reports,
            "messages": [],
            "stats": stats,
        }

    def _query_stats(self, task_id: str) -> dict[str, Any] | None:
        """Query TaskRun stats if the DB is available; return None otherwise."""
        try:
            from app.core.database import get_session_factory
            from app.models import TaskRun

            session = get_session_factory()()
            try:
                task_run = session.get(TaskRun, task_id)
                if task_run is None:
                    return None
                return {
                    "status": task_run.status,
                    "durationMs": task_run.duration_ms,
                    "inputTokens": task_run.input_tokens,
                    "outputTokens": task_run.output_tokens,
                    "totalTokens": task_run.total_tokens,
                }
            finally:
                session.close()
        except Exception:
            return None

    def cancel(self, task_id: str) -> bool:
        """Request cancellation. Returns True if a task was found."""
        task = self.tasks.get(task_id)
        if task is None:
            return False
        return task.cancel()


# Module-level singleton (mirrors WorkflowApplication.instance).
_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
