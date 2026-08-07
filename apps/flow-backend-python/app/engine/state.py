"""Flat execution State — the LangGraph state shape.

Per the IR contract (§3), every node output becomes a State field named
``{nodeId}__{fieldName}``. To make LangGraph **merge** partial updates from
each node (rather than replace the whole state), we declare a TypedDict with
``Annotated[dict, merge_reducer]`` channels: node outputs flow into the ``data``
dict, and reserved metadata (inputs/outputs/status) live in their own channels.

A bare ``dict`` schema would NOT merge — each node's return value would replace
the entire state. The TypedDict + reducers here are load-bearing.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _merge_dict(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer: shallow-merge right into left (right wins on key conflict)."""
    out = dict(left or {})
    if right:
        out.update(right)
    return out


# Channel names — these ARE the FlowState TypedDict field names. Node fns and
# helpers return partial updates keyed by these names; LangGraph merges them.
INPUTS_KEY = "inputs"
OUTPUTS_KEY = "outputs"
TASK_ID_KEY = "task_id"
NODE_STATUS_KEY = "node_status"
WORKFLOW_STATUS_KEY = "workflow_status"
BREAK_KEY = "break_signal"
DATA_KEY = "data"


class FlowState(TypedDict, total=False):
    """LangGraph state schema. Each channel uses a merge reducer so node fns
    can return partial updates (e.g. just their own outputs) and have them
    merged into the running state."""

    # All node outputs accumulate here: {nodeId__field: value, ...}.
    data: Annotated[dict[str, Any], _merge_dict]
    inputs: dict[str, Any]
    outputs: Annotated[dict[str, Any], _merge_dict]
    task_id: str
    node_status: Annotated[dict[str, Any], _merge_dict]
    workflow_status: str
    break_signal: Annotated[bool, lambda a, b: a or b]  # OR: once True, stays True


def new_state(task_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a fresh State for a task run."""
    return {
        DATA_KEY: {},
        INPUTS_KEY: inputs,
        OUTPUTS_KEY: {},
        TASK_ID_KEY: task_id,
        NODE_STATUS_KEY: {},
        WORKFLOW_STATUS_KEY: "processing",
        BREAK_KEY: False,
    }


def get_inputs(state: dict[str, Any]) -> dict[str, Any]:
    return state.get(INPUTS_KEY, {})


def get_outputs(state: dict[str, Any]) -> dict[str, Any]:
    return state.get(OUTPUTS_KEY, {})


def set_workflow_status(state: dict[str, Any], status: str) -> None:
    state[WORKFLOW_STATUS_KEY] = status


def get_workflow_status(state: dict[str, Any]) -> str:
    return state.get(WORKFLOW_STATUS_KEY, "processing")


def is_terminated(state: dict[str, Any]) -> bool:
    """True if the workflow reached a terminal state (matches Node's `terminated`)."""
    return get_workflow_status(state) in {"succeeded", "failed", "canceled"}


def set_node_status(state: dict[str, Any], node_id: str, status: str) -> None:
    state.setdefault(NODE_STATUS_KEY, {})[node_id] = status


def get_data(state: dict[str, Any]) -> dict[str, Any]:
    """Return the node-outputs dict ({nodeId__field: value})."""
    return state.get(DATA_KEY, {})
