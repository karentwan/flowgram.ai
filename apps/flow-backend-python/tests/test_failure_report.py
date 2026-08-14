"""Failure-report tests — the editor must see per-node results on failure.

LangGraph raises (instead of returning state) when a node fails, so the report
must still carry: succeeded nodes' status/snapshots, the failing node marked
``failed`` with an error snapshot, and messages.error entries. Mirrors Node's
status/snapshot/message centers surviving a failed run.
"""

from __future__ import annotations

import asyncio

import pytest

from app.engine.runner import get_task_manager


async def _wait(tm, task_id: str) -> None:
    task = tm.tasks[task_id]
    if task.future is not None:
        try:
            await task.future
        except asyncio.CancelledError:
            pass


def _wf_with_code(code_script: str) -> dict:
    """start → code → end workflow with a user code node."""
    return {
        "nodes": [
            {
                "id": "start_0",
                "type": "start",
                "meta": {"position": {"x": 0, "y": 0}},
                "data": {
                    "outputs": {
                        "type": "object",
                        "properties": {"n": {"type": "number"}},
                    }
                },
            },
            {
                "id": "code_0",
                "type": "code",
                "meta": {"position": {"x": 100, "y": 0}},
                "data": {
                    "script": {"language": "python", "content": code_script},
                    "inputsValues": {"n": {"type": "ref", "content": ["start_0", "n"]}},
                },
            },
            {
                "id": "end_0",
                "type": "end",
                "meta": {"position": {"x": 200, "y": 0}},
                "data": {
                    "inputs": {"type": "object"},
                    "inputsValues": {"out": {"type": "ref", "content": ["code_0", "result"]}},
                },
            },
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "code_0"},
            {"sourceNodeID": "code_0", "targetNodeID": "end_0"},
        ],
    }


class TestFailureReport:
    @pytest.mark.asyncio
    async def test_failed_run_reports_succeeded_and_failed_nodes(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(_wf_with_code("x = 1"), {"n": 1})  # missing main() → fails
        await _wait(tm, task_id)

        report = tm.report(task_id)
        assert report is not None
        assert report["workflowStatus"] == {"status": "failed", "terminated": True}

        reports = report["reports"]
        # start succeeded with its snapshot…
        assert reports["start_0"]["status"] == "succeeded"
        assert len(reports["start_0"]["snapshots"]) >= 1
        # …the failing code node is marked failed with an error snapshot…
        assert reports["code_0"]["status"] == "failed"
        code_snaps = reports["code_0"]["snapshots"]
        assert len(code_snaps) >= 1
        assert "main" in code_snaps[0]["error"]
        # …and the downstream end node never ran, so it has no report entry.
        assert "end_0" not in reports

        # Error messages carry nodeID (editor shows "node: message" + node bar).
        errors = report["messages"]["error"]
        assert any(m.get("nodeID") == "code_0" and "main" in m["message"] for m in errors)

        # Node timing present so the status bar renders its cost tag.
        assert isinstance(reports["code_0"]["startTime"], int)
        assert reports["code_0"]["timeCost"] >= 0

    @pytest.mark.asyncio
    async def test_failed_node_snapshot_contains_resolved_inputs(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(_wf_with_code("x = 1"), {"n": 42})
        await _wait(tm, task_id)

        report = tm.report(task_id)
        assert report is not None
        snap = report["reports"]["code_0"]["snapshots"][0]
        assert snap["inputs"] == {"n": 42}

    @pytest.mark.asyncio
    async def test_graph_build_failure_reports_workflow_error(self) -> None:
        """A schema error outside any node must still surface a message."""
        tm = get_task_manager()
        bad = {
            "nodes": [
                {
                    "id": "start_0",
                    "type": "start",
                    "meta": {"position": {"x": 0, "y": 0}},
                    "data": {"outputs": {"type": "object", "properties": {}}},
                },
                {
                    "id": "wat_0",
                    "type": "no-such-node-type",
                    "meta": {"position": {"x": 100, "y": 0}},
                    "data": {},
                },
            ],
            "edges": [{"sourceNodeID": "start_0", "targetNodeID": "wat_0"}],
        }
        task_id = tm.run(bad, {})
        await _wait(tm, task_id)

        report = tm.report(task_id)
        assert report is not None
        assert report["workflowStatus"]["status"] == "failed"
        errors = report["messages"]["error"]
        assert len(errors) >= 1
        assert errors[0].get("nodeID") is None

    @pytest.mark.asyncio
    async def test_fanout_failure_keeps_failed_node_and_succeeded_siblings(self) -> None:
        """start → a → {b(raises), c(succeeds)}: the failing branch and its
        succeeded sibling must BOTH appear in the report (LangGraph passes the
        same pre-superstep state to each branch node, so the live mirror must
        not let sibling touches clobber each other's progress)."""
        wf = {
            "nodes": [
                {
                    "id": "start_0",
                    "type": "start",
                    "meta": {"position": {"x": 0, "y": 0}},
                    "data": {"outputs": {"type": "object", "properties": {}}},
                },
                {
                    "id": "a_0",
                    "type": "code",
                    "meta": {"position": {"x": 100, "y": 0}},
                    "data": {
                        "script": {
                            "language": "python",
                            "content": "def main(params):\n    return {'v': 1}\n",
                        },
                        "inputsValues": {},
                    },
                },
                {
                    "id": "b_0",
                    "type": "code",
                    "meta": {"position": {"x": 200, "y": -50}},
                    "data": {
                        "script": {
                            "language": "python",
                            "content": "def main(params):\n    raise ValueError('boom')\n",
                        },
                        "inputsValues": {},
                    },
                },
                {
                    "id": "c_0",
                    "type": "code",
                    "meta": {"position": {"x": 200, "y": 50}},
                    "data": {
                        "script": {
                            "language": "python",
                            "content": "def main(params):\n    return {'v2': 2}\n",
                        },
                        "inputsValues": {},
                    },
                },
            ],
            "edges": [
                {"sourceNodeID": "start_0", "targetNodeID": "a_0"},
                {"sourceNodeID": "a_0", "targetNodeID": "b_0"},
                {"sourceNodeID": "a_0", "targetNodeID": "c_0"},
            ],
        }
        tm = get_task_manager()
        task_id = tm.run(wf, {})
        await _wait(tm, task_id)

        report = tm.report(task_id)
        assert report is not None
        assert report["workflowStatus"]["status"] == "failed"
        reports = report["reports"]
        assert reports["a_0"]["status"] == "succeeded"
        assert reports["c_0"]["status"] == "succeeded"
        assert reports["c_0"]["snapshots"][0]["outputs"] == {"v2": 2}
        assert reports["b_0"]["status"] == "failed"
        assert "boom" in reports["b_0"]["snapshots"][0]["error"]

    @pytest.mark.asyncio
    async def test_successful_run_report_keeps_node_timings_and_empty_messages(self) -> None:
        tm = get_task_manager()
        task_id = tm.run(
            _wf_with_code("def main(params):\n    return {'result': params.get('n')}\n"),
            {"n": 7},
        )
        await _wait(tm, task_id)

        report = tm.report(task_id)
        assert report is not None
        assert report["workflowStatus"] == {"status": "succeeded", "terminated": True}
        assert report["reports"]["end_0"]["status"] == "succeeded"
        assert report["messages"]["error"] == []
