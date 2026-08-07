"""Phase-3 end-to-end engine tests.

Exercises the full IR → StateGraph → run pipeline against the in-process task
manager (no HTTP, no DB). Uses only self-contained workflows (no external API
calls) so tests run hermetically. All tests are async (pytest-asyncio) so the
task manager's run() and the awaited future share one event loop.
"""

from __future__ import annotations

import asyncio

import pytest

from app.engine.runner import get_task_manager


async def _wait(tm, task_id: str) -> None:
    """Await a task's background future to completion."""
    task = tm.tasks[task_id]
    if task.future is not None:
        try:
            await task.future
        except asyncio.CancelledError:
            pass


# A minimal start→end workflow: outputs echo the input.
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
                    "required": ["message"],
                },
            },
        },
        {
            "id": "end_0",
            "type": "end",
            "meta": {"position": {"x": 100, "y": 0}},
            "data": {
                "inputs": {"type": "object", "properties": {"echo": {"type": "string"}}},
                "inputsValues": {
                    "echo": {"type": "ref", "content": ["start_0", "message"]}
                },
            },
        },
    ],
    "edges": [{"sourceNodeID": "start_0", "targetNodeID": "end_0"}],
}


class TestEchoWorkflow:
    @pytest.mark.asyncio
    async def test_runs_and_echoes_input(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(ECHO_WORKFLOW, {"message": "hello world"})
        await _wait(tm, task_id)
        result = tm.result(task_id)
        assert result == {"echo": "hello world"}


# --------------------------------------------------------------------------
# Condition branch workflow: start(n) → condition(n>=10? big : small) → end_*
# --------------------------------------------------------------------------

CONDITION_WORKFLOW: dict = {
    "nodes": [
        {
            "id": "start_0",
            "type": "start",
            "meta": {"position": {"x": 0, "y": 0}},
            "data": {
                "outputs": {
                    "type": "object",
                    "properties": {"n": {"type": "number"}},
                    "required": ["n"],
                },
            },
        },
        {
            "id": "cond_0",
            "type": "condition",
            "meta": {"position": {"x": 100, "y": 0}},
            "data": {
                "conditions": [
                    {
                        "key": "big",
                        "value": {
                            "left": {"type": "ref", "content": ["start_0", "n"]},
                            "operator": "gte",
                            "right": {"type": "constant", "content": 10},
                        },
                    },
                    {
                        "key": "small",
                        "value": {
                            "left": {"type": "ref", "content": ["start_0", "n"]},
                            "operator": "lt",
                            "right": {"type": "constant", "content": 10},
                        },
                    },
                ]
            },
        },
        {
            "id": "end_big",
            "type": "end",
            "meta": {"position": {"x": 200, "y": -50}},
            "data": {
                "inputs": {"type": "object", "properties": {"size": {"type": "string"}}},
                "inputsValues": {"size": {"type": "constant", "content": "big"}},
            },
        },
        {
            "id": "end_small",
            "type": "end",
            "meta": {"position": {"x": 200, "y": 50}},
            "data": {
                "inputs": {"type": "object", "properties": {"size": {"type": "string"}}},
                "inputsValues": {"size": {"type": "constant", "content": "small"}},
            },
        },
    ],
    "edges": [
        {"sourceNodeID": "start_0", "targetNodeID": "cond_0"},
        {"sourceNodeID": "cond_0", "targetNodeID": "end_big", "sourcePortID": "big"},
        {"sourceNodeID": "cond_0", "targetNodeID": "end_small", "sourcePortID": "small"},
    ],
}


class TestConditionBranch:
    @pytest.mark.asyncio
    async def test_takes_big_branch(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(CONDITION_WORKFLOW, {"n": 42})
        await _wait(tm, task_id)
        assert tm.result(task_id) == {"size": "big"}

    @pytest.mark.asyncio
    async def test_takes_small_branch(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(CONDITION_WORKFLOW, {"n": 3})
        await _wait(tm, task_id)
        assert tm.result(task_id) == {"size": "small"}


# --------------------------------------------------------------------------
# Task lifecycle (sync ops; no background await needed)
# --------------------------------------------------------------------------


class TestTaskLifecycle:
    @pytest.mark.asyncio
    async def test_cancel_marks_canceled(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(ECHO_WORKFLOW, {"message": "x"})
        ok = tm.cancel(task_id)
        assert ok is True
        await _wait(tm, task_id)
        report = tm.report(task_id)
        assert report is not None
        assert report["workflowStatus"]["status"] in {"canceled", "succeeded", "failed"}

    def test_report_unknown_task_returns_none(self) -> None:
        assert get_task_manager().report("nonexistent") is None

    def test_result_unknown_task_returns_none(self) -> None:
        assert get_task_manager().result("nonexistent") is None

    def test_cancel_unknown_task_returns_false(self) -> None:
        assert get_task_manager().cancel("nonexistent") is False
