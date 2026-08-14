"""Node executor base helpers.

Each node type is implemented as a factory: ``make_<type>_node(node_ir)`` returns
a LangGraph node function ``async def fn(state) -> dict``. The function reads
upstream values from ``state`` and returns a partial state update (its outputs
as ``{nodeId}__{field}`` keys).
"""

from __future__ import annotations

import time
from typing import Any, Callable

from app.core.logging import get_logger
from app.engine import live_state
from app.engine.state import DATA_KEY, NODE_STATUS_KEY, SNAPSHOTS_KEY, TASK_ID_KEY
from app.engine.values import resolve_inputs_values
from app.schemas.ir import WorkflowNode

# A LangGraph node function: takes state, returns a partial state update.
NodeFn = Callable[[dict[str, Any]], dict[str, Any]]

_log = get_logger(__name__)

# Module-level registry of active observability recorders, keyed by task_id.
# Set by the runner when a task starts; node fns look up their recorder here to
# record per-node events without threading a DB session through LangGraph state.
_recorders: dict[str, Any] = {}


def register_recorder(task_id: str, recorder: Any) -> None:
    _recorders[task_id] = recorder


def unregister_recorder(task_id: str) -> None:
    _recorders.pop(task_id, None)


def outputs_for(node: WorkflowNode, values: dict[str, Any]) -> dict[str, Any]:
    """Build a partial-state update writing each output into the data channel."""
    return {DATA_KEY: {f"{node.id}__{k}": v for k, v in values.items()}}


def wrap_with_status(node: WorkflowNode, fn: NodeFn) -> NodeFn:
    """Wrap a node fn to record status + notify the observability recorder.

    Status is returned in the partial update (not mutated on input state) so
    LangGraph's merge reducer accumulates it correctly.

    Failure handling mirrors Node's engine: the failing node is marked
    ``failed``, a snapshot with the error is attached, and an error message is
    recorded — via the per-task live-state mirror — so the editor can render
    succeeded nodes + the failing node (with its error) even though LangGraph
    raises instead of returning state.
    """

    node_id = node.id
    node_type = node.type

    async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        _log.info("node start", node_id=node_id, node_type=node_type)
        task_id = state.get(TASK_ID_KEY, "")
        start_ms = time.time() * 1000
        live_state.touch(task_id, state)
        recorder = _recorders.get(task_id)
        if recorder is not None:
            recorder.start_node(node_id, node_type, 0)
        try:
            result = await fn(state)  # type: ignore[misc]
        except Exception as e:
            error_message = str(e) or type(e).__name__
            _log.error("node failed", node_id=node_id, error=error_message)
            try:
                inputs = resolve_inputs_values(get_inputs_values(node), state)
            except Exception:
                inputs = {}
            live_state.mark_node_failed(task_id, node_id, error_message, inputs)
            live_state.record_node_time(task_id, node_id, start_ms, time.time() * 1000 - start_ms)
            if recorder is not None:
                recorder.end_node(node_id, node_type, 0, "failed", error=error_message)
            raise
        result = dict(result)
        result[NODE_STATUS_KEY] = {node_id: "succeeded"}
        usage = _extract_usage(result)
        outputs = _extract_node_outputs(result)
        # Push a snapshot for this node so the editor can render results under
        # it. Outputs are stripped of the `{nodeId}__` prefix so they show as
        # field names (matches Node's snapshot.outputs shape).
        stripped = {k.split("__", 1)[1] if k.startswith(f"{node_id}__") else k: v for k, v in outputs.items()}
        result[SNAPSHOTS_KEY] = [{"nodeID": node_id, "inputs": None, "outputs": stripped}]
        live_state.merge_update(task_id, result)
        live_state.record_node_time(task_id, node_id, start_ms, time.time() * 1000 - start_ms)
        if recorder is not None:
            recorder.end_node(node_id, node_type, 0, "succeeded", outputs, usage)
        _log.info("node end", node_id=node_id)
        return result

    return wrapped


def _extract_usage(result: dict[str, Any]) -> dict[str, int]:
    """Pull token usage out of a node's returned data channel (LLM/agent)."""
    data = result.get(DATA_KEY, {}) or {}
    for k, v in data.items():
        if k.endswith("__usage") and isinstance(v, dict):
            return v
    return {}


def _extract_node_outputs(result: dict[str, Any]) -> dict[str, Any]:
    """Return the node's outputs (from the data channel) for observability."""
    return result.get(DATA_KEY, {}) or {}


def get_inputs_values(node: WorkflowNode) -> dict[str, Any]:
    """Fetch the node's ``data.inputsValues`` (canvas-bound input values)."""
    return (node.data.get("inputsValues") or node.data.get("inputValues") or {})
