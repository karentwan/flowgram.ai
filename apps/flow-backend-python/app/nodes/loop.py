"""Loop node executor (serial mode — parallel mode lands in phase 4).

Phase-3 scope: serial loop only (``mode == 'serial'`` or unset). Parallel mode
(``Send`` + ``Semaphore``) is the grill core need and lands in phase 4.

Serial loop semantics (contract §5):
  - Iterate ``loopFor`` array in order.
  - For each item, run the loop body subgraph with ``{loopId}_locals`` scope
    populated (item, index).
  - Collect each iteration's outputs (per ``loopOutputs`` refs) and aggregate
    into per-output arrays.
  - ``break`` node stops further iterations.

The loop body is itself a LangGraph subgraph, built by the loader. Here we
accept a pre-built subgraph callable and drive it.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.engine.state import BREAK_KEY
from app.engine.values import resolve_ref
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode

# A body runner: given (state, item, index, loop_id), execute the loop body and
# return a dict of {output_name: value} collected for this iteration.
BodyRunner = Callable[[dict[str, Any], Any, int, str], Awaitable[dict[str, Any]]]


def make_loop_node(node: WorkflowNode, body_runner: BodyRunner | None = None) -> NodeFn:
    """Build a serial-mode loop node fn.

    ``body_runner`` is supplied by the loader (it builds the loop body subgraph
    and wraps it into this callable). If None, the loop body is a no-op
    (used for tests / pre-phase-3 stubs).
    """
    loop_for_ref = node.data.get("loopFor")
    loop_outputs_decl = node.data.get("loopOutputs") or {}
    mode = node.data.get("mode") or "serial"

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        # Resolve the array to iterate.
        loop_array = resolve_ref(loop_for_ref, state) if loop_for_ref else None
        if not isinstance(loop_array, list):
            loop_array = []

        # Aggregated outputs: {output_name: [values...]}.
        aggregated: dict[str, list[Any]] = {name: [] for name in loop_outputs_decl}

        for index, item in enumerate(loop_array):
            locals_map = {"item": item, "index": index}
            if body_runner is not None:
                iter_outputs = await body_runner(state, item, index, node.id)
            else:
                iter_outputs = {}

            # Collect declared outputs for this iteration.
            for name in loop_outputs_decl:
                aggregated[name].append(iter_outputs.get(name))

            # break: stop further iterations (serial semantics).
            if state.get(BREAK_KEY):
                break

        return outputs_for(node, {name: vals for name, vals in aggregated.items()})

    return wrap_with_status(node.id, fn)
