"""Node executor base helpers.

Each node type is implemented as a factory: ``make_<type>_node(node_ir)`` returns
a LangGraph node function ``async def fn(state) -> dict``. The function reads
upstream values from ``state`` and returns a partial state update (its outputs
as ``{nodeId}__{field}`` keys).

Node executors share these helpers for writing outputs and recording status.
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.logging import get_logger
from app.engine.state import DATA_KEY, NODE_STATUS_KEY, set_node_status
from app.schemas.ir import WorkflowNode

# A LangGraph node function: takes state, returns a partial state update.
NodeFn = Callable[[dict[str, Any]], dict[str, Any]]

_log = get_logger(__name__)


def outputs_for(node: WorkflowNode, values: dict[str, Any]) -> dict[str, Any]:
    """Build a partial-state update writing each output into the data channel.

    Returns ``{DATA_KEY: {nodeId__field: value, ...}}`` so the merge reducer
    accumulates outputs from every node without overwriting prior ones.
    """
    return {DATA_KEY: {f"{node.id}__{k}": v for k, v in values.items()}}


def wrap_with_status(node_id: str, fn: NodeFn) -> NodeFn:
    """Wrap a node fn so it records status (running→succeeded/failed) and logs.

    Status is returned in the partial update (not mutated on the input state)
    so LangGraph's merge reducer accumulates it correctly.
    """

    async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        _log.info("node start", node_id=node_id)
        try:
            result = await fn(state)  # type: ignore[misc]
        except Exception as e:
            _log.error("node failed", node_id=node_id, error=str(e))
            # Return a partial update marking failure (re-raise after logging).
            raise
        # Merge node_status into the returned partial update.
        result = dict(result)
        result[NODE_STATUS_KEY] = {node_id: "succeeded"}
        _log.info("node end", node_id=node_id)
        return result

    return wrapped


def get_inputs_values(node: WorkflowNode) -> dict[str, Any]:
    """Fetch the node's ``data.inputsValues`` (canvas-bound input values)."""
    return (node.data.get("inputsValues") or node.data.get("inputValues") or {})
