"""Phase-4 loop concurrency tests — serial vs parallel, break in both modes.

Uses a fake BodyRunner with asyncio.sleep to observe concurrency speedup and
verify index alignment. No external API calls (hermetic).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.engine.state import BREAK_KEY, DATA_KEY, new_state
from app.nodes.loop import make_loop_node
from app.schemas.ir import WorkflowNode


def _loop_node(mode: str | None, semaphore: int | None = None) -> WorkflowNode:
    """Build a minimal loop WorkflowNode IR."""
    data: dict[str, Any] = {
        "loopFor": {"type": "ref", "content": ["start_0", "items"]},
        "loopOutputs": {"result": {"type": "ref", "content": ["body_0", "out"]}},
    }
    if mode is not None:
        data["mode"] = mode
    if semaphore is not None:
        data["semaphore"] = semaphore
    return WorkflowNode(id="loop_0", type="loop", meta=None, data=data)


def _state_with_items(items: list[Any]) -> dict[str, Any]:
    """State with items seeded into the data channel (as start_0 would)."""
    state = new_state("t1", {})
    state[DATA_KEY] = {"start_0__items": items}
    return state


# --------------------------------------------------------------------------
# Fake body runner — sleeps DELAY seconds, returns {result: f"done-{idx}"}.
# Records concurrent in-flight count so we can assert parallelism.
# --------------------------------------------------------------------------


def _make_sleeping_runner(delay: float = 0.1, track_concurrency: bool = False):
    """Return (runner, max_concurrency_holder)."""
    inflight = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def runner(state, item, index, loop_id):
        nonlocal inflight, max_seen
        if track_concurrency:
            async with lock:
                inflight += 1
                max_seen = max(max_seen, inflight)
        await asyncio.sleep(delay)
        if track_concurrency:
            async with lock:
                inflight -= 1
        # Echo the item so we can verify index alignment.
        return {"result": f"done-{item}"}

    return runner, lambda: max_seen


# --------------------------------------------------------------------------
# Serial mode
# --------------------------------------------------------------------------


class TestSerialMode:
    @pytest.mark.asyncio
    async def test_serial_runs_all_in_order(self) -> None:
        runner, _ = _make_sleeping_runner(delay=0.01)
        node = _loop_node(mode="serial")
        fn = make_loop_node(node, body_runner=runner)
        state = _state_with_items(["a", "b", "c", "d"])
        result = await fn(state)
        # Outputs land in the data channel under loop_0__result.
        assert result["data"]["loop_0__result"] == ["done-a", "done-b", "done-c", "done-d"]

    @pytest.mark.asyncio
    async def test_serial_is_sequential(self) -> None:
        """4 items × 0.05s serial ≈ 0.2s (not 0.05s)."""
        runner, max_seen = _make_sleeping_runner(delay=0.05, track_concurrency=True)
        node = _loop_node(mode="serial")
        fn = make_loop_node(node, body_runner=runner)
        start = time.monotonic()
        await fn(_state_with_items([1, 2, 3, 4]))
        elapsed = time.monotonic() - start
        assert elapsed >= 0.18  # ~4×0.05
        assert max_seen() == 1  # never more than 1 in flight


# --------------------------------------------------------------------------
# Parallel mode
# --------------------------------------------------------------------------


class TestParallelMode:
    @pytest.mark.asyncio
    async def test_parallel_speedup(self) -> None:
        """4 items × 0.1s with semaphore=4 ≈ 0.1s (not 0.4s)."""
        runner, max_seen = _make_sleeping_runner(delay=0.1, track_concurrency=True)
        node = _loop_node(mode="parallel", semaphore=4)
        fn = make_loop_node(node, body_runner=runner)
        start = time.monotonic()
        await fn(_state_with_items([1, 2, 3, 4]))
        elapsed = time.monotonic() - start
        assert elapsed < 0.3  # parallel: ~0.1s, well under serial 0.4s
        assert max_seen() >= 2  # actual concurrency observed

    @pytest.mark.asyncio
    async def test_parallel_preserves_index_order(self) -> None:
        """Results align to original index regardless of completion order."""
        # Stagger delays so later items finish first (would disorder naive append).
        async def runner(state, item, index, loop_id):
            # Item 0 sleeps longest, item 3 shortest — completion order reversed.
            await asyncio.sleep(0.15 - index * 0.04)
            return {"result": f"item-{index}"}

        node = _loop_node(mode="parallel", semaphore=4)
        fn = make_loop_node(node, body_runner=runner)
        result = await fn(_state_with_items([0, 1, 2, 3]))
        # Index alignment: results[i] corresponds to loopFor[i].
        assert result["data"]["loop_0__result"] == ["item-0", "item-1", "item-2", "item-3"]

    @pytest.mark.asyncio
    async def test_parallel_semaphore_caps_concurrency(self) -> None:
        """semaphore=2 → max in-flight never exceeds 2."""
        runner, max_seen = _make_sleeping_runner(delay=0.08, track_concurrency=True)
        node = _loop_node(mode="parallel", semaphore=2)
        fn = make_loop_node(node, body_runner=runner)
        await fn(_state_with_items([1, 2, 3, 4, 5, 6]))
        assert max_seen() <= 2

    @pytest.mark.asyncio
    async def test_parallel_no_semaphore_unlimited(self) -> None:
        """No semaphore → all 4 run at once."""
        runner, max_seen = _make_sleeping_runner(delay=0.08, track_concurrency=True)
        node = _loop_node(mode="parallel")  # no semaphore
        fn = make_loop_node(node, body_runner=runner)
        await fn(_state_with_items([1, 2, 3, 4]))
        assert max_seen() == 4

    @pytest.mark.asyncio
    async def test_parallel_empty_array(self) -> None:
        runner, _ = _make_sleeping_runner(delay=0.01)
        node = _loop_node(mode="parallel", semaphore=4)
        fn = make_loop_node(node, body_runner=runner)
        result = await fn(_state_with_items([]))
        assert result["data"]["loop_0__result"] == []


# --------------------------------------------------------------------------
# Break in both modes
# --------------------------------------------------------------------------


class TestBreakSemantics:
    @pytest.mark.asyncio
    async def test_serial_break_stops_loop(self) -> None:
        """In serial mode, break flag stops further iterations."""
        call_log: list[int] = []

        async def runner(state, item, index, loop_id):
            call_log.append(index)
            # Set break after the 2nd iteration (index 1).
            if index == 1:
                state[BREAK_KEY] = True
            return {"result": f"i-{index}"}

        node = _loop_node(mode="serial")
        fn = make_loop_node(node, body_runner=runner)
        await fn(_state_with_items([0, 1, 2, 3, 4]))
        # Only indices 0,1 ran; 2,3,4 never started.
        assert call_log == [0, 1]

    @pytest.mark.asyncio
    async def test_parallel_break_keeps_index_alignment(self) -> None:
        """In parallel mode, break doesn't corrupt index alignment — remaining
        indices that didn't complete get None placeholders."""
        completed: list[int] = []

        async def runner(state, item, index, loop_id):
            await asyncio.sleep(0.05)
            completed.append(index)
            return {"result": f"i-{index}"}

        node = _loop_node(mode="parallel", semaphore=1)  # force sequential-ish
        fn = make_loop_node(node, body_runner=runner)
        state = _state_with_items([0, 1, 2, 3])
        # Pre-set break so only index 0 runs before cancellation.
        # (In real graphs break is set by a break node mid-iteration; here we
        # simulate the post-iteration check by having the runner set it.)
        async def runner_with_break(state, item, index, loop_id):
            await asyncio.sleep(0.01)
            if index == 0:
                state[BREAK_KEY] = True
            return {"result": f"i-{index}"}

        node2 = _loop_node(mode="parallel", semaphore=1)
        fn2 = make_loop_node(node2, body_runner=runner_with_break)
        result = await fn2(_state_with_items([0, 1, 2, 3]))
        # With semaphore=1 + break at index 0, behavior mirrors serial.
        # Index alignment preserved (None for un-run iterations).
        results = result["data"]["loop_0__result"]
        assert len(results) == 4
        assert results[0] == "i-0"


# --------------------------------------------------------------------------
# semaphore validation (defensive)
# --------------------------------------------------------------------------


class TestSemaphoreValidation:
    @pytest.mark.asyncio
    async def test_invalid_semaphore_falls_back_to_unlimited(self) -> None:
        runner, max_seen = _make_sleeping_runner(delay=0.05, track_concurrency=True)
        node = _loop_node(mode="parallel", semaphore=-1)  # invalid
        fn = make_loop_node(node, body_runner=runner)
        await fn(_state_with_items([1, 2, 3]))
        # Invalid semaphore → unlimited → all run at once.
        assert max_seen() == 3

    @pytest.mark.asyncio
    async def test_semaphore_clamped_to_soft_cap(self) -> None:
        """semaphore=100 → clamped to 20 (defensive; canvas also warns)."""
        # Just verify it runs without error (clamping is internal).
        runner, _ = _make_sleeping_runner(delay=0.01)
        node = _loop_node(mode="parallel", semaphore=100)
        fn = make_loop_node(node, body_runner=runner)
        result = await fn(_state_with_items([1, 2, 3]))
        assert len(result["data"]["loop_0__result"]) == 3
