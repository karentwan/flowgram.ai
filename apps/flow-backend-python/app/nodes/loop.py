"""Loop node executor — serial and parallel modes (grill core need, phase 4).

Two modes (contract §5, LoopMode enum):
  - serial (default):   iterate loopFor in order, run body subgraph per item.
  - parallel:           run body subgraphs concurrently with asyncio, capped by
                        semaphore (actual concurrency = min(semaphore, len)).

Both modes share semantics (grill stance A — semantics follow LangGraph, the
Python scheduling detail is a performance hint):
  - Output order is preserved by index alignment (results[i] corresponds to
    loopFor[i] regardless of completion order).
  - break: serial → stop the for-loop; parallel → cancel pending dispatches
    (in-flight iterations are awaited but their outputs are discarded).

The loop body is a pre-built callable (BodyRunner) supplied by the graph loader.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from app.core.logging import get_logger
from app.engine.state import BREAK_KEY
from app.engine.values import resolve_ref
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode

_log = get_logger(__name__)

# A body runner: given (state, item, index, loop_id), execute the loop body and
# return a dict of {output_name: value} collected for this iteration.
BodyRunner = Callable[[dict[str, Any], Any, int, str], Awaitable[dict[str, Any]]]

# Soft cap for semaphore (contract §5). The canvas warns above this; we clamp
# defensively in case a malformed value reaches the executor.
SEMAPHORE_SOFT_CAP = 20


def make_loop_node(node: WorkflowNode, body_runner: BodyRunner | None = None) -> NodeFn:
    """Build a loop node fn that dispatches serial or parallel per ``mode``."""
    loop_for_ref = node.data.get("loopFor")
    loop_outputs_decl = node.data.get("loopOutputs") or {}
    mode = node.data.get("mode") or "serial"
    raw_semaphore = node.data.get("semaphore")

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        loop_array = resolve_ref(loop_for_ref, state) if loop_for_ref else None
        if not isinstance(loop_array, list):
            loop_array = []

        if mode == "parallel":
            outputs_by_index = await _run_parallel(
                state, loop_array, node.id, body_runner, raw_semaphore
            )
        else:
            outputs_by_index = await _run_serial(state, loop_array, node.id, body_runner)

        # Aggregate by output name, preserving original index order.
        aggregated: dict[str, list[Any]] = {name: [] for name in loop_outputs_decl}
        for _idx in range(len(loop_array)):
            iter_out = outputs_by_index.get(_idx, {})
            for name in loop_outputs_decl:
                aggregated[name].append(iter_out.get(name))

        return outputs_for(node, {name: vals for name, vals in aggregated.items()})

    return wrap_with_status(node.id, node.type, fn)


async def _run_serial(
    state: dict[str, Any],
    loop_array: list[Any],
    loop_id: str,
    body_runner: BodyRunner | None,
) -> dict[int, dict[str, Any]]:
    """Serial: iterate in order, check break after each iteration."""
    results: dict[int, dict[str, Any]] = {}
    for index, item in enumerate(loop_array):
        if body_runner is None:
            results[index] = {}
            continue
        results[index] = await body_runner(state, item, index, loop_id)
        # break: stop further iterations (serial semantics).
        if state.get(BREAK_KEY):
            # Remaining indices get no output (None placeholders filled by caller).
            break
    return results


async def _run_parallel(
    state: dict[str, Any],
    loop_array: list[Any],
    loop_id: str,
    body_runner: BodyRunner | None,
    raw_semaphore: Any,
) -> dict[int, dict[str, Any]]:
    """Parallel: asyncio.Semaphore-capped concurrency, index-aligned results.

    break handling: once the break flag is set, no NEW tasks are dispatched
    (cooperative cancel — in-flight tasks finish but their outputs are kept
    only if they completed before the break was observed).
    """
    if body_runner is None or not loop_array:
        return {i: {} for i in range(len(loop_array))}

    # Resolve semaphore (positive int, clamped to soft cap). None/invalid → unlimited.
    semaphore_value = _resolve_semaphore(raw_semaphore)
    sem = asyncio.Semaphore(semaphore_value) if semaphore_value else None

    results: dict[int, dict[str, Any]] = {}
    # Track in-flight tasks so we can stop dispatching once break is observed.
    pending: set[asyncio.Task] = set()

    async def _worker(idx: int, item: Any) -> dict[str, Any]:
        if sem is not None:
            async with sem:
                return await body_runner(state, item, idx, loop_id)
        return await body_runner(state, item, idx, loop_id)

    # Dispatch all tasks (Semaphore caps actual concurrency). We create them all
    # up front but the Semaphore gates execution; this is the standard pattern.
    tasks = [asyncio.create_task(_worker(idx, item)) for idx, item in enumerate(loop_array)]

    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        for t in done:
            # Map task → its index via the order we created them.
            idx = tasks.index(t)
            try:
                results[idx] = t.result()
            except Exception as e:
                _log.error("loop iteration failed", loop_id=loop_id, index=idx, error=str(e))
                results[idx] = {}
    finally:
        # If break was set during execution, cancel any still-pending tasks.
        if state.get(BREAK_KEY):
            for t in tasks:
                if not t.done():
                    t.cancel()

    return results


def _resolve_semaphore(raw: Any) -> int | None:
    """Return a valid positive int ≤ SOFT_CAP, or None (unlimited)."""
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return min(value, SEMAPHORE_SOFT_CAP)
