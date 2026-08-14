"""Per-task live-execution mirror — keeps per-node progress visible on failure.

LangGraph's ``ainvoke`` does NOT return the state when a node raises: partial
progress (node statuses, snapshots, outputs) is silently lost, so the editor's
report comes back empty for a mid-workflow failure — the canvas shows nothing
and the only trace is the backend log. Node's runtime avoids this because its
status/snapshot/message centers live OUTSIDE the execution state.

We mirror that design: node wrappers update a small per-task registry as they
run (latest merged State copy + per-node timings + workflow messages), and the
TaskManager folds it back into ``task.state`` when the run terminates — on
success AND on failure — so ``report()`` always has full per-node detail:

  - succeeded nodes keep their status + result snapshots,
  - the failing node is marked ``failed`` with a snapshot carrying ``error``,
  - ``messages.error`` carries ``{nodeID, message}`` entries the editor renders.

The registry is keyed by task_id, lives for one run, and is cleared by the
runner (module-level state mirrors the recorder registry in nodes/base.py).
"""

from __future__ import annotations

import time
from typing import Any

from app.engine.state import (
    DATA_KEY,
    INPUTS_KEY,
    NODE_STATUS_KEY,
    OUTPUTS_KEY,
    SNAPSHOTS_KEY,
)
from app.engine.state import (
    merge_update as _merge_into_state,
)


def _empty_messages() -> dict[str, list[dict[str, Any]]]:
    return {"log": [], "info": [], "debug": [], "error": [], "warning": []}


# task_id → {"state": {...}, "node_times": {...}, "messages": {...}}
_live: dict[str, dict[str, Any]] = {}


def _entry(task_id: str) -> dict[str, Any]:
    entry = _live.get(task_id)
    if entry is None:
        entry = {"state": {}, "node_times": {}, "messages": _empty_messages()}
        _live[task_id] = entry
    return entry


def _copy_state(state: dict[str, Any]) -> dict[str, Any]:
    """Copy the channels we mutate (so LangGraph's own state objects stay clean)."""
    out = dict(state)
    for k in (NODE_STATUS_KEY, DATA_KEY, OUTPUTS_KEY, INPUTS_KEY):
        v = out.get(k)
        if isinstance(v, dict):
            out[k] = dict(v)
    v = out.get(SNAPSHOTS_KEY)
    if isinstance(v, list):
        out[SNAPSHOTS_KEY] = list(v)
    return out


def touch(task_id: str, state: dict[str, Any]) -> None:
    """Stash a copy of the earliest State a task has seen.

    Initialize-only on purpose: in a fan-out LangGraph passes the same
    pre-superstep state to every branch node, so overwriting on each touch
    would erase sibling branches' progress already recorded via
    ``merge_update``/``mark_node_failed``. Per-node progress accumulates
    through those merge calls instead; the first touch only seeds the mirror
    with the initial channels (inputs, task_id, workflow_status, ...).
    """
    entry = _entry(task_id)
    if not entry["state"]:
        entry["state"] = _copy_state(state)


def merge_update(task_id: str, update: dict[str, Any]) -> None:
    """Merge a node fn's returned partial update into the mirror."""
    entry = _entry(task_id)
    _merge_into_state(entry["state"], update)


def mark_node_failed(
    task_id: str, node_id: str, error: str, inputs: dict[str, Any] | None
) -> None:
    """Node.js parity for a failing node:
    ``nodeStatus(node.id).fail()`` + ``snapshot.update({error})`` +
    ``messageCenter.error({nodeID, message})``.
    """
    entry = _entry(task_id)
    _merge_into_state(entry["state"], {NODE_STATUS_KEY: {node_id: "failed"}})
    _merge_into_state(
        entry["state"],
        {SNAPSHOTS_KEY: [{"nodeID": node_id, "inputs": inputs, "outputs": {}, "error": error}]},
    )
    entry["messages"]["error"].append(
        {
            "id": f"{node_id}-error-{len(entry['messages']['error'])}",
            "type": "error",
            "message": error,
            "nodeID": node_id,
            "timestamp": int(time.time() * 1000),
        }
    )


def add_message(task_id: str, message: str, node_id: str | None = None) -> None:
    """Record a workflow-level error message (no nodeID)."""
    entry = _entry(task_id)
    entry["messages"]["error"].append(
        {
            "id": f"workflow-error-{len(entry['messages']['error'])}",
            "type": "error",
            "message": message,
            "nodeID": node_id,
            "timestamp": int(time.time() * 1000),
        }
    )


def has_node_error(task_id: str) -> bool:
    """True if any recorded error message is attached to a node."""
    entry = _live.get(task_id)
    if entry is None:
        return False
    return any(m.get("nodeID") for m in entry["messages"].get("error", []))


def record_node_time(task_id: str, node_id: str, start_ms: float, time_cost_ms: float) -> None:
    """Record per-node timing (startTime/timeCost) for the report."""
    entry = _entry(task_id)
    entry["node_times"][node_id] = {"start_time": start_ms, "time_cost": time_cost_ms}


def take(task_id: str) -> dict[str, Any] | None:
    """Pop and return the live entry (state/node_times/messages), or None."""
    return _live.pop(task_id, None)


def clear(task_id: str) -> None:
    """Drop a task's live entry (runner calls this in its finally block)."""
    _live.pop(task_id, None)
