"""IR loader: parse + validate a WorkflowSchema JSON into a WorkflowIR.

This is the Python entry point for the LangGraph IR contract
(packages/runtime/interface/src/langgraph-ir/contract.md). Phase 1 implements
**parsing + structural validation only** — building the actual LangGraph
StateGraph is deferred to phase 3.

Validation rules (contract §2, §6):
  - Reject unknown node `type` values (not in NODE_TYPE_TO_PYTHON_MODULE).
  - Reject REMOVED_NODE_TYPES (`continue`) explicitly with a clear message.
  - Reject `expression` FlowValues (not exported by TS interface; contract §3).
  - Forward-compat: tolerate unknown `data` fields on recognized node types.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.logging import get_logger
from app.schemas.ir import (
    NODE_TYPE_TO_PYTHON_MODULE,
    REMOVED_NODE_TYPES,
    FlowValue,
    WorkflowIR,
    WorkflowNode,
)

_log = get_logger(__name__)


class IRLoaderError(ValueError):
    """Raised when a WorkflowSchema JSON violates the IR contract."""


def _validate_node_recursive(node: WorkflowNode, path: str) -> None:
    """Recursively validate a node and its nested subgraph (loop body)."""
    node_type = node.type
    node_path = f"{path} → {node.type}({node.id})"

    if node_type in REMOVED_NODE_TYPES:
        raise IRLoaderError(
            f"Node type '{node_type}' was removed and is no longer supported "
            f"(at {node_path}). Replace it with conditional edges or break."
        )

    if node_type not in NODE_TYPE_TO_PYTHON_MODULE:
        raise IRLoaderError(
            f"Unknown node type '{node_type}' (at {node_path}). The Python "
            "executor has no handler for this type."
        )

    # Reject `expression` FlowValues anywhere in this node's inputsValues.
    inputs_values = node.data.get("inputsValues") or node.data.get("inputValues") or {}
    if isinstance(inputs_values, dict):
        for key, raw in inputs_values.items():
            if not isinstance(raw, dict) or raw.get("type") != "expression":
                continue
            try:
                FlowValue.model_validate(raw)
            except ValidationError:
                pass
            else:
                # expression is syntactically valid but contractually rejected.
                raise IRLoaderError(
                    f"'expression' FlowValues are not supported (at {node_path}, "
                    f"inputsValues.{key}). Use 'template' or 'ref' instead."
                )

    # Recurse into nested subgraph (loop body).
    for child in node.blocks or []:
        _validate_node_recursive(child, node_path)


def load_ir(schema: dict[str, Any] | str) -> WorkflowIR:
    """Parse a WorkflowSchema JSON (dict or string) into a validated WorkflowIR.

    Raises IRLoaderError on any contract violation.
    """
    if isinstance(schema, str):
        try:
            import json

            schema = json.loads(schema)
        except json.JSONDecodeError as e:
            raise IRLoaderError(f"schema is not valid JSON: {e}") from e

    try:
        ir = WorkflowIR.model_validate(schema)
    except ValidationError as e:
        raise IRLoaderError(f"schema does not match WorkflowIR shape: {e}") from e

    # Structural validation beyond Pydantic: node types, removed features.
    for node in ir.nodes:
        _validate_node_recursive(node, "workflow")

    _log.info(
        "ir loaded",
        node_count=len(ir.nodes),
        edge_count=len(ir.edges),
        has_global_variable=ir.global_variable is not None,
    )
    return ir
