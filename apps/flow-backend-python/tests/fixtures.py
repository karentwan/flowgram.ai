"""Shared IR test fixtures: a minimal valid workflow (start→llm→end).

Mirrors the shape of packages/runtime/js-core/src/domain/__tests__/schemas/
but stripped to what the phase-1 loader needs (no execution, just parse).
"""

from __future__ import annotations

# A minimal valid workflow IR: start → llm → end.
# Variable refs use the contract §3 path shape ['nodeId','field'].
SIMPLE_WORKFLOW_IR: dict = {
    "nodes": [
        {
            "id": "start_0",
            "type": "start",
            "meta": {"position": {"x": 0, "y": 0}},
            "data": {
                "title": "Start",
                "outputs": {
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": ["topic"],
                },
            },
        },
        {
            "id": "llm_0",
            "type": "llm",
            "meta": {"position": {"x": 100, "y": 0}},
            "data": {
                "title": "LLM",
                "inputsValues": {
                    "modelName": {"type": "constant", "content": "gpt-4o-mini"},
                    "prompt": {"type": "template", "content": "Write about {{start_0__topic}}"},
                },
                "inputs": {
                    "type": "object",
                    "properties": {
                        "modelName": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["modelName", "prompt"],
                },
                "outputs": {"type": "object", "properties": {"result": {"type": "string"}}},
            },
        },
        {
            "id": "end_0",
            "type": "end",
            "meta": {"position": {"x": 200, "y": 0}},
            "data": {
                "title": "End",
                "inputs": {"type": "object", "properties": {"answer": {"type": "string"}}},
                "inputsValues": {
                    "answer": {"type": "ref", "content": ["llm_0", "result"]}
                },
            },
        },
    ],
    "edges": [
        {"sourceNodeID": "start_0", "targetNodeID": "llm_0"},
        {"sourceNodeID": "llm_0", "targetNodeID": "end_0"},
    ],
    "globalVariable": None,
}

# A workflow containing a (removed) continue node — loader must reject.
WORKFLOW_WITH_CONTINUE: dict = {
    "nodes": [
        {"id": "start_0", "type": "start", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
        {"id": "c_0", "type": "continue", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
    ],
    "edges": [{"sourceNodeID": "start_0", "targetNodeID": "c_0"}],
}

# A workflow with an unknown node type — loader must reject.
WORKFLOW_WITH_UNKNOWN_TYPE: dict = {
    "nodes": [
        {"id": "start_0", "type": "start", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
        {"id": "x_0", "type": "flux-capacitor", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
    ],
    "edges": [{"sourceNodeID": "start_0", "targetNodeID": "x_0"}],
}

# A nested loop workflow (serial mode default) exercising the recursive validator.
LOOP_WORKFLOW_IR: dict = {
    "nodes": [
        {
            "id": "start_0",
            "type": "start",
            "meta": {"position": {"x": 0, "y": 0}},
            "data": {
                "outputs": {
                    "type": "object",
                    "properties": {"tasks": {"type": "array", "items": {"type": "string"}}},
                },
            },
        },
        {
            "id": "loop_0",
            "type": "loop",
            "meta": {"position": {"x": 100, "y": 0}},
            "data": {
                "title": "Loop",
                "loopFor": {"type": "ref", "content": ["start_0", "tasks"]},
                "loopOutputs": {
                    "results": {"type": "ref", "content": ["llm_0", "result"]},
                },
            },
            "blocks": [
                {"id": "bs_0", "type": "block-start", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
                {
                    "id": "llm_0",
                    "type": "llm",
                    "meta": {"position": {"x": 50, "y": 0}},
                    "data": {
                        "inputsValues": {
                            "prompt": {
                                "type": "template",
                                "content": "{{loop_0_locals.item}}",
                            }
                        },
                        "outputs": {"type": "object", "properties": {"result": {"type": "string"}}},
                    },
                },
                {"id": "be_0", "type": "block-end", "meta": {"position": {"x": 100, "y": 0}}, "data": {}},
            ],
            "edges": [
                {"sourceNodeID": "bs_0", "targetNodeID": "llm_0"},
                {"sourceNodeID": "llm_0", "targetNodeID": "be_0"},
            ],
        },
    ],
    "edges": [
        {"sourceNodeID": "start_0", "targetNodeID": "loop_0"},
    ],
}
