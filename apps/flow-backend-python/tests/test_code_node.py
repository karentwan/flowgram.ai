"""Code node + graph integration tests (phase 5).

Code node is self-contained (no external calls) so we test it directly. MCP/
Agent nodes mirror Node's protocol exactly and require live servers; their
behavioral parity is verified by protocol-level assertions in the executor
code (JSON-RPC envelope shape, response parsing) rather than end-to-end here.
"""

from __future__ import annotations

import pytest

from app.engine.graph import build_graph
from app.engine.state import new_state
from app.nodes.code import make_code_node
from app.schemas.ir import WorkflowNode


class TestCodeNode:
    @pytest.mark.asyncio
    async def test_runs_user_python_main(self) -> None:
        node = WorkflowNode(
            id="code_0",
            type="code",
            meta=None,
            data={
                "code": "def main(params):\n    return {'doubled': params['n'] * 2}",
                "inputsValues": {"n": {"type": "constant", "content": 21}},
            },
        )
        fn = make_code_node(node)
        state = new_state("t", {})
        result = await fn(state)
        assert result["data"]["code_0__doubled"] == 42

    @pytest.mark.asyncio
    async def test_missing_main_raises(self) -> None:
        node = WorkflowNode(
            id="code_0",
            type="code",
            meta=None,
            data={"code": "x = 1", "inputsValues": {}},
        )
        fn = make_code_node(node)
        with pytest.raises(RuntimeError, match="must define.*main"):
            await fn(new_state("t", {}))

    @pytest.mark.asyncio
    async def test_non_dict_result_wrapped(self) -> None:
        node = WorkflowNode(
            id="code_0",
            type="code",
            meta=None,
            data={"code": "def main(params):\n    return 99", "inputsValues": {}},
        )
        fn = make_code_node(node)
        result = await fn(new_state("t", {}))
        assert result["data"]["code_0__result"] == 99


class TestGraphWithCode:
    @pytest.mark.asyncio
    async def test_start_code_end_pipeline(self) -> None:
        """start(n) → code(doubler) → end references code output."""
        wf = {
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
                        "code": "def main(params):\n    return {'doubled': params['n'] * 2}",
                        "inputsValues": {
                            "n": {"type": "ref", "content": ["start_0", "n"]}
                        },
                    },
                },
                {
                    "id": "end_0",
                    "type": "end",
                    "meta": {"position": {"x": 200, "y": 0}},
                    "data": {
                        "inputs": {"type": "object"},
                        "inputsValues": {
                            "answer": {"type": "ref", "content": ["code_0", "doubled"]}
                        },
                    },
                },
            ],
            "edges": [
                {"sourceNodeID": "start_0", "targetNodeID": "code_0"},
                {"sourceNodeID": "code_0", "targetNodeID": "end_0"},
            ],
        }
        graph = build_graph(wf)
        result = await graph.ainvoke(new_state("t1", {"n": 21}))
        assert result["outputs"] == {"answer": 42}
