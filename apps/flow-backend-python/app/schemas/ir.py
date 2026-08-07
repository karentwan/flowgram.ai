"""Pydantic models mirroring FlowGram's WorkflowSchema (the canvas IR product).

These models are the Python-side parse target for the LangGraph IR contract
(see packages/runtime/interface/src/langgraph-ir/contract.md). The TS canvas
emits WorkflowSchema JSON; the Python loader parses it into these models before
building a LangGraph StateGraph.

Field names here deliberately match the TS `WorkflowSchema`/`WorkflowNodeSchema`
shape (camelCase) so the JSON round-trips without key translation. Pydantic
`alias`es are used where Pythonic snake_case attributes are wanted internally.
"""

from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------
# Constants — MUST stay in sync with
# packages/runtime/interface/src/langgraph-ir/constant.ts
# --------------------------------------------------------------------------

STATE_FIELD_SEPARATOR = "__"
LOOP_LOCALS_SUFFIX = "_locals"
ENCRYPTED_VALUE_PREFIX = "enc::"

# Node types the Python executor recognizes. Mirrors
# NODE_TYPE_TO_PYTHON_MODULE on the TS side. Value=None means "structurally
# present in canvas JSON, ignored by executor" (block markers / visual nodes).
NODE_TYPE_TO_PYTHON_MODULE: dict[str, str | None] = {
    "start": "start",
    "end": "end",
    "llm": "llm",
    "http": "http",
    "code": "code",
    "condition": "condition",
    "loop": "loop",
    "break": "break",
    "mcp": "mcp",
    "agent": "agent",
    # Subgraph boundary markers — present in canvas, ignored by executor.
    "block-start": None,
    "block-end": None,
    # Visual-only.
    "comment": None,
    "group": None,
    "root": None,
}

# Node types explicitly removed by the grill decision. Loader rejects these.
REMOVED_NODE_TYPES: frozenset[str] = frozenset({"continue"})


# --------------------------------------------------------------------------
# FlowValue union (mirrors IFlowValue in schema/value.ts)
# --------------------------------------------------------------------------

FlowValueType: TypeAlias = Literal["constant", "ref", "expression", "template"]


class FlowValue(BaseModel):
    """A FlowValue is one of: constant | ref | template | expression.

    Discriminated by `type`. Kept as a permissive model since each node type
    interprets the payload differently; strict validation happens in node
    executors. (expression is not exported by the TS interface and is rejected
    by the loader — see contract.md §3.)
    """

    model_config = ConfigDict(extra="allow")

    type: FlowValueType
    content: Any = None


# --------------------------------------------------------------------------
# JSON Schema (mirrors IJsonSchema in schema/json-schema.ts)
# --------------------------------------------------------------------------


class JsonSchema(BaseModel):
    """Minimal JSON Schema subset used by node inputs/outputs declarations.

    Mirrors IJsonSchema — intentionally permissive (extra keys allowed) because
    the canvas emits form-component hints (`extra.formComponent`) the executor
    ignores.
    """

    model_config = ConfigDict(extra="allow")

    type: str | None = None
    default: Any = None
    title: str | None = None
    description: str | None = None
    enum: list[str | int | float] | None = None
    properties: dict[str, JsonSchema] | None = None
    additional_properties: JsonSchema | None = Field(default=None, alias="additionalProperties")
    items: JsonSchema | None = None
    required: list[str] | None = None
    ref: str | None = Field(default=None, alias="$ref")


# --------------------------------------------------------------------------
# Node / Edge / Workflow (mirror schema/node.ts, schema/edge.ts, workflow.ts)
# --------------------------------------------------------------------------


class WorkflowNodeMeta(BaseModel):
    """Visual-only metadata. Ignored by the executor (contract §1)."""

    model_config = ConfigDict(extra="allow")

    position: dict[str, float] | None = None
    canvas_position: dict[str, float] | None = Field(default=None, alias="canvasPosition")


class WorkflowEdge(BaseModel):
    """Control-flow edge. Branch via `source_port_id` (= ConditionItem.key)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    source_node_id: str = Field(alias="sourceNodeID")
    target_node_id: str = Field(alias="targetNodeID")
    source_port_id: str | None = Field(default=None, alias="sourcePortID")
    target_port_id: str | None = Field(default=None, alias="targetPortID")


class WorkflowNode(BaseModel):
    """A workflow node. Recursive via `blocks` (nested subgraph, e.g. loop body)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    type: str
    meta: WorkflowNodeMeta | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    blocks: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


class WorkflowIR(BaseModel):
    """Top-level IR: the parsed WorkflowSchema product from the canvas.

    This is what `POST /task/run` receives as the `schema` field (after JSON
    parse). The loader validates it then builds a LangGraph StateGraph.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    groups: list[dict[str, Any]] | None = None  # visual-only
    global_variable: JsonSchema | None = Field(default=None, alias="globalVariable")


# --------------------------------------------------------------------------
# Helpers (mirror state-field.ts on the TS side)
# --------------------------------------------------------------------------


def build_state_field(node_id: str, field_name: str) -> str:
    """Build a flat LangGraph State field name. Invariant: `{nodeId}__{field}`.

    Mirrors buildStateField() in langgraph-ir/state-field.ts exactly.
    """
    return f"{node_id}{STATE_FIELD_SEPARATOR}{field_name}"


def is_loop_locals_scope(s: str) -> bool:
    """True if `s` is a synthetic loop-locals scope id (e.g. `loop_0_locals`)."""
    return s.endswith(LOOP_LOCALS_SUFFIX)


def resolve_ref_path(
    path: list[str],
) -> dict[str, Any] | None:
    """Resolve an IFlowRefValue.content path.

    Returns one of:
      {"field": "<state_field>"}                     # standard node ref
      {"field": "<state_field>", "nested": [...]}    # nested key tail
      {"loop_locals": "item"|"index"|...}            # loop iteration var
      None                                            # unrecognized shape

    Mirrors resolveRefPath() in langgraph-ir/state-field.ts.
    """
    if not isinstance(path, list) or not path:
        return None

    head = path[0]
    if isinstance(head, str) and is_loop_locals_scope(head):
        second = path[1] if len(path) > 1 else ""
        return {"loop_locals": second}

    if len(path) >= 2:
        field = build_state_field(head, path[1])
        rest = path[2:]
        return {"field": field, "nested": rest} if rest else {"field": field}

    return None
