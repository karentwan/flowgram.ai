"""Phase-1 IR loader tests: parsing + contract validation (no graph building)."""

from __future__ import annotations

import pytest

from app.engine.loader import IRLoaderError, load_ir
from app.schemas.ir import (
    NODE_TYPE_TO_PYTHON_MODULE,
    REMOVED_NODE_TYPES,
    build_state_field,
    is_loop_locals_scope,
    resolve_ref_path,
)

from .fixtures import (
    LOOP_WORKFLOW_IR,
    SIMPLE_WORKFLOW_IR,
    WORKFLOW_WITH_CONTINUE,
    WORKFLOW_WITH_UNKNOWN_TYPE,
)


# --------------------------------------------------------------------------
# Helpers (mirror TS state-field.ts) — keep both sides in lockstep
# --------------------------------------------------------------------------


class TestStateFieldHelpers:
    def test_build_state_field(self) -> None:
        assert build_state_field("llm_0", "result") == "llm_0__result"
        assert build_state_field("a", "b") == "a__b"

    def test_is_loop_locals_scope(self) -> None:
        assert is_loop_locals_scope("loop_0_locals") is True
        assert is_loop_locals_scope("loop_0") is False
        assert is_loop_locals_scope("start_0") is False

    def test_resolve_ref_standard(self) -> None:
        assert resolve_ref_path(["llm_0", "result"]) == {"field": "llm_0__result"}

    def test_resolve_ref_nested(self) -> None:
        out = resolve_ref_path(["http_0", "body", "name"])
        assert out == {"field": "http_0__body", "nested": ["name"]}

    def test_resolve_ref_loop_locals(self) -> None:
        assert resolve_ref_path(["loop_0_locals", "item"]) == {"loop_locals": "item"}
        assert resolve_ref_path(["loop_0_locals", "index"]) == {"loop_locals": "index"}

    def test_resolve_ref_empty(self) -> None:
        assert resolve_ref_path([]) is None
        assert resolve_ref_path(["lonely"]) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Contract constants sanity
# --------------------------------------------------------------------------


class TestContractConstants:
    def test_continue_is_removed(self) -> None:
        assert "continue" in REMOVED_NODE_TYPES

    def test_known_types_all_mapped(self) -> None:
        # Every recognized type is either mapped to a module or explicitly None.
        for t, mod in NODE_TYPE_TO_PYTHON_MODULE.items():
            assert mod is None or isinstance(mod, str)

    def test_block_markers_are_ignored(self) -> None:
        assert NODE_TYPE_TO_PYTHON_MODULE["block-start"] is None
        assert NODE_TYPE_TO_PYTHON_MODULE["block-end"] is None


# --------------------------------------------------------------------------
# load_ir — happy paths
# --------------------------------------------------------------------------


class TestLoadIRHappy:
    def test_parses_simple_workflow(self) -> None:
        ir = load_ir(SIMPLE_WORKFLOW_IR)
        assert len(ir.nodes) == 3
        assert {n.type for n in ir.nodes} == {"start", "llm", "end"}
        # camelCase edge aliases round-trip
        assert ir.edges[0].source_node_id == "start_0"
        assert ir.edges[0].target_node_id == "llm_0"

    def test_parses_string_schema(self) -> None:
        import json

        ir = load_ir(json.dumps(SIMPLE_WORKFLOW_IR))
        assert len(ir.nodes) == 3

    def test_parses_loop_workflow_recursive(self) -> None:
        ir = load_ir(LOOP_WORKFLOW_IR)
        loop = next(n for n in ir.nodes if n.type == "loop")
        assert loop.blocks is not None
        assert len(loop.blocks) == 3  # block-start, llm, block-end
        assert {b.type for b in loop.blocks} == {"block-start", "llm", "block-end"}

    def test_tolerates_unknown_data_fields(self) -> None:
        """Forward-compat: recognized node type with unknown data fields is OK."""
        wf = {
            "nodes": [
                {
                    "id": "start_0",
                    "type": "start",
                    "meta": {"position": {"x": 0, "y": 0}},
                    "data": {"title": "Start", "futureField": {"unknown": True}},
                }
            ],
            "edges": [],
        }
        ir = load_ir(wf)
        assert ir.nodes[0].data["futureField"] == {"unknown": True}


# --------------------------------------------------------------------------
# load_ir — rejection paths
# --------------------------------------------------------------------------


class TestLoadIRRejection:
    def test_rejects_continue_node(self) -> None:
        with pytest.raises(IRLoaderError, match="removed"):
            load_ir(WORKFLOW_WITH_CONTINUE)

    def test_rejects_unknown_node_type(self) -> None:
        with pytest.raises(IRLoaderError, match="Unknown node type"):
            load_ir(WORKFLOW_WITH_UNKNOWN_TYPE)

    def test_rejects_invalid_json_string(self) -> None:
        with pytest.raises(IRLoaderError, match="not valid JSON"):
            load_ir("{not json")

    def test_rejects_continue_in_nested_subgraph(self) -> None:
        """A continue buried in a loop body must still be caught."""
        wf = {
            "nodes": [
                {"id": "start_0", "type": "start", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
                {
                    "id": "loop_0",
                    "type": "loop",
                    "meta": {"position": {"x": 0, "y": 0}},
                    "data": {},
                    "blocks": [
                        {
                            "id": "c_0",
                            "type": "continue",
                            "meta": {"position": {"x": 0, "y": 0}},
                            "data": {},
                        }
                    ],
                    "edges": [],
                },
            ],
            "edges": [],
        }
        with pytest.raises(IRLoaderError, match="removed"):
            load_ir(wf)
