"""Observability layer tests (phase 6, grill route 2).

Verifies TaskRun + NodeExecution rows are written during execution and the
report endpoint surfaces stats (token totals, duration, status).
"""

from __future__ import annotations

import pytest

from app.engine.runner import get_task_manager
from app.models import NodeExecution, TaskRun


async def _wait(tm, task_id: str) -> None:
    import asyncio

    task = tm.tasks[task_id]
    if task.future is not None:
        try:
            await task.future
        except asyncio.CancelledError:
            pass


ECHO_WORKFLOW: dict = {
    "nodes": [
        {
            "id": "start_0",
            "type": "start",
            "meta": {"position": {"x": 0, "y": 0}},
            "data": {
                "outputs": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                }
            },
        },
        {
            "id": "end_0",
            "type": "end",
            "meta": {"position": {"x": 100, "y": 0}},
            "data": {
                "inputs": {"type": "object"},
                "inputsValues": {
                    "echo": {"type": "ref", "content": ["start_0", "message"]}
                },
            },
        },
    ],
    "edges": [{"sourceNodeID": "start_0", "targetNodeID": "end_0"}],
}


class TestObservabilityRecording:
    @pytest.mark.asyncio
    async def test_task_run_recorded_on_completion(self, sqlite_engine, db_session) -> None:
        from app.core import database

        database.configure_engine(sqlite_engine)
        tm = get_task_manager()
        task_id = tm.run(ECHO_WORKFLOW, {"message": "hi"})
        await _wait(tm, task_id)

        # TaskRun row should reflect success.
        task_run = db_session.get(TaskRun, task_id)
        assert task_run is not None
        assert task_run.status == "succeeded"
        assert task_run.duration_ms >= 0
        assert task_run.outputs == {"echo": "hi"}

    @pytest.mark.asyncio
    async def test_node_executions_recorded(self, sqlite_engine, db_session) -> None:
        from app.core import database

        database.configure_engine(sqlite_engine)
        tm = get_task_manager()
        task_id = tm.run(ECHO_WORKFLOW, {"message": "hi"})
        await _wait(tm, task_id)

        node_execs = db_session.query(NodeExecution).all()
        # At least start + end nodes should have records.
        assert len(node_execs) >= 2
        node_ids = {ne.node_id for ne in node_execs}
        assert "start_0" in node_ids
        assert "end_0" in node_ids

    @pytest.mark.asyncio
    async def test_report_includes_stats(self, sqlite_engine) -> None:
        from app.core import database

        database.configure_engine(sqlite_engine)
        tm = get_task_manager()
        task_id = tm.run(ECHO_WORKFLOW, {"message": "hi"})
        await _wait(tm, task_id)
        report = tm.report(task_id)
        assert report is not None
        assert "stats" in report
        stats = report["stats"]
        assert stats is not None
        assert stats["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_failed_task_records_error(self, sqlite_engine, db_session) -> None:
        """A workflow that throws should record status=failed + error message."""
        from app.core import database

        database.configure_engine(sqlite_engine)
        bad_wf = {
            "nodes": [
                {
                    "id": "start_0",
                    "type": "start",
                    "meta": {"position": {"x": 0, "y": 0}},
                    "data": {"outputs": {"type": "object", "properties": {}}},
                },
                {
                    "id": "code_0",
                    "type": "code",
                    "meta": {"position": {"x": 100, "y": 0}},
                    # Missing main() → raises at runtime.
                    "data": {
                        "script": {"language": "python", "content": "x = 1"},
                        "inputsValues": {},
                    },
                },
            ],
            "edges": [{"sourceNodeID": "start_0", "targetNodeID": "code_0"}],
        }
        tm = get_task_manager()
        task_id = tm.run(bad_wf, {})
        await _wait(tm, task_id)
        task_run = db_session.get(TaskRun, task_id)
        assert task_run is not None
        assert task_run.status == "failed"
        assert task_run.error is not None
