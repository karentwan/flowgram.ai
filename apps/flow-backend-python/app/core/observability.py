"""Observability service (grill route 2): records execution events to stats tables.

Grill decision: post-hoc query (R1) via structlog + business stats tables.
This module writes TaskRun + NodeExecution rows during execution so the report
endpoint and SQL aggregation can answer L3 questions (token totals, per-node
duration, State replay).

Designed to be NON-BLOCKING: if the DB is unavailable, observations degrade
to log-only (execution proceeds). Observability must never break a workflow run.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import NodeExecution, TaskRun

_log = get_logger(__name__)


class ObservabilityRecorder:
    """Records task/node execution events. One instance per task run."""

    def __init__(self, session: Session | None, task_id: str) -> None:
        self.session = session
        self.task_id = task_id
        self._task_started = time.monotonic()
        # In-progress node timers: (node_id, iteration) → start_monotonic
        self._node_starts: dict[tuple[str, int], float] = {}

    def start_node(
        self, node_id: str, node_type: str, iteration: int, inputs: dict[str, Any] | None = None
    ) -> None:
        self._node_starts[(node_id, iteration)] = time.monotonic()
        self._try_write(
            lambda: self._session_add(
                NodeExecution(
                    task_id=self.task_id,
                    node_id=node_id,
                    node_type=node_type,
                    iteration=iteration,
                    status="running",
                    inputs=inputs,
                )
            )
        )

    def end_node(
        self,
        node_id: str,
        node_type: str,
        iteration: int,
        status: str,
        outputs: dict[str, Any] | None = None,
        usage: dict[str, int] | None = None,
        error: str | None = None,
    ) -> None:
        start = self._node_starts.pop((node_id, iteration), None)
        duration_ms = int((time.monotonic() - start) * 1000) if start else 0
        usage = usage or {}
        node_exec = NodeExecution(
            task_id=self.task_id,
            node_id=node_id,
            node_type=node_type,
            iteration=iteration,
            status=status,
            outputs=outputs,
            input_tokens=int(usage.get("input_tokens", 0) or usage.get("inputTokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or usage.get("outputTokens", 0) or 0),
            duration_ms=duration_ms,
            error=error[:2000] if error else None,
        )
        # Upsert: we already inserted a "running" row; simplest correct path is
        # a second completed row. For MVP that's acceptable (two rows: started +
        # finished); a unique constraint + update would be the follow-up.
        self._try_write(lambda: self._session_add(node_exec))

    def finish_task(
        self,
        status: str,
        outputs: dict[str, Any] | None,
        state_snapshot: dict[str, Any] | None,
        total_usage: dict[str, int] | None,
        error: str | None = None,
    ) -> None:
        duration_ms = int((time.monotonic() - self._task_started) * 1000)
        total_usage = total_usage or {}
        self._try_write(
            lambda: self._session_merge_task(
                status=status,
                outputs=outputs,
                state_snapshot=state_snapshot,
                input_tokens=int(total_usage.get("input_tokens", 0) or 0),
                output_tokens=int(total_usage.get("output_tokens", 0) or 0),
                total_tokens=int(total_usage.get("total_tokens", 0) or 0),
                duration_ms=duration_ms,
                error=error,
            )
        )

    # --- internals ---

    def _session_add(self, obj: Any) -> None:
        if self.session is None:
            return
        self.session.add(obj)
        self.session.commit()

    def _session_merge_task(
        self,
        status: str,
        outputs: dict[str, Any] | None,
        state_snapshot: dict[str, Any] | None,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        duration_ms: int,
        error: str | None,
    ) -> None:
        if self.session is None:
            return
        task = self.session.get(TaskRun, self.task_id)
        if task is None:
            return
        task.status = status
        task.outputs = outputs
        task.state_snapshot = state_snapshot
        task.input_tokens = input_tokens
        task.output_tokens = output_tokens
        task.total_tokens = total_tokens
        task.duration_ms = duration_ms
        task.error = error[:2000] if error else None
        self.session.commit()

    def _try_write(self, fn) -> None:
        if self.session is None:
            return
        try:
            fn()
        except Exception as e:
            # Observability must never break execution.
            _log.warning("observability write failed", task_id=self.task_id, error=str(e))
            try:
                self.session.rollback()
            except Exception:
                pass


def create_task_run_record(session: Session | None, task_id: str, inputs: dict[str, Any]) -> None:
    """Insert the initial TaskRun row at task start (status=processing)."""
    if session is None:
        return
    try:
        session.add(TaskRun(id=task_id, status="processing", inputs=inputs))
        session.commit()
    except Exception as e:
        _log.warning("task run record insert failed", task_id=task_id, error=str(e))
        try:
            session.rollback()
        except Exception:
            pass
