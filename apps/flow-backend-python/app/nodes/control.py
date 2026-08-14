"""Start / End node executors.

start: graph entry. Reads run inputs (POST /task/run `inputs`) and seeds them
into State as ``start_0__<field>`` for every declared output property.
end: graph exit. Resolves ``data.inputsValues`` and writes them to the reserved
``__outputs__`` key as the workflow's final result.
"""

from __future__ import annotations

from typing import Any

from app.engine.state import OUTPUTS_KEY, get_inputs
from app.engine.values import resolve_inputs_values
from app.nodes.base import NodeFn, get_inputs_values, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode


def make_start_node(node: WorkflowNode) -> NodeFn:
    """start node: seed declared outputs from run inputs."""
    declared = (((node.data.get("outputs") or {}).get("properties")) or {}).keys()

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        inputs = get_inputs(state)
        # Seed each declared output field from the matching input key.
        values = {field: inputs.get(field) for field in declared}
        return outputs_for(node, values)

    return wrap_with_status(node, fn)


def make_end_node(node: WorkflowNode) -> NodeFn:
    """end node: assemble final outputs from inputsValues and stash under __outputs__."""
    inputs_values = get_inputs_values(node)

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        resolved = resolve_inputs_values(inputs_values, state)
        return {OUTPUTS_KEY: resolved}

    return wrap_with_status(node, fn)
