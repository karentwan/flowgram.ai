"""Variable reference resolution — turns canvas FlowValues into concrete values.

FlowValue types (mirror IFlowValue in schema/value.ts):
  - constant: literal value  → {type:'constant', content: <any>}
  - ref:     path reference  → {type:'ref', content: ['nodeId','field',...?]}
  - template: interpolation  → {type:'template', content: 'hi {{nodeId__field}}'}
  - expression: REJECTED by loader (contract §3)

Node outputs live in the ``data`` channel of the State (``state['__data__']``)
as ``{nodeId}__{field}`` keys. Refs and templates read from there.
"""

from __future__ import annotations

import re
from typing import Any

from app.engine.state import DATA_KEY, get_inputs

# Matches {{ path }} in template strings. Supports non-ASCII keys (e.g. Chinese
# field names like 服务商编号) and dot-nested paths (nodeId__field.sub).
# `[^.{}\s]+` matches any char except `.`, braces, and whitespace — covers
# Chinese/unicode identifiers that `\w` would miss.
_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([^.{}\s]+(?:\.[^.{}\s]+)*)\s*\}\}")


def _locals_from_state(state: dict[str, Any], scope_id: str) -> dict[str, Any] | None:
    """Recover loop locals from state when locals_map wasn't passed.

    The loop body runner stashes locals under state["__loop_locals__"][loop_id].
    ``scope_id`` is the ``loopId_locals`` form (e.g. ``loop_RER-F_locals``);
    we strip the ``_locals`` suffix to get the loop_id key.
    """
    if not isinstance(scope_id, str) or not scope_id.endswith("_locals"):
        return None
    loop_id = scope_id[: -len("_locals")]
    stash = state.get("__loop_locals__", {})
    return stash.get(loop_id)


def resolve_ref(value: dict[str, Any], state: dict[str, Any], locals_map: dict[str, Any] | None = None) -> Any:
    """Resolve a ref FlowValue (``{type:'ref', content: [path...]}``).

    Returns the referenced value, or None if unresolved.
    """
    path = value.get("content") or []
    if not isinstance(path, list) or not path:
        return None

    head = path[0]

    # Loop-locals scope: ['loopId_locals', 'item'] or ['loopId_locals', 'item', 'sub']
    # → locals_map['item'], then drill into ['sub'] if nested.
    if isinstance(head, str) and head.endswith("_locals"):
        # If locals_map wasn't passed, try to recover it from state (loop body
        # nodes call resolvers without a locals_map arg; the runner stashes
        # locals in state keyed by loop_id).
        if locals_map is None:
            locals_map = _locals_from_state(state, head)
        if locals_map is None:
            return None
        if len(path) < 2:
            return None
        current: Any = locals_map.get(path[1])
        for seg in path[2:]:
            if isinstance(seg, str) and isinstance(current, dict):
                current = current.get(seg)
            else:
                return None
        return current

    # Standard node ref: ['nodeId', 'field', ...nested?]
    if len(path) >= 2 and isinstance(head, str) and isinstance(path[1], str):
        data = state.get(DATA_KEY, {})
        field_key = f"{head}__{path[1]}"
        current: Any = data.get(field_key)
        if current is None:
            # Fall back to inputs dict if the start node hasn't run yet.
            current = get_inputs(state).get(path[1])
        if current is None:
            # Debug: log unresolved refs so missing upstream outputs surface.
            from app.core.logging import get_logger as _gl
            _gl(__name__).warning(
                "ref unresolved",
                path=path,
                field_key=field_key,
                available_keys=list(data.keys()),
            )
        for seg in path[2:]:
            if isinstance(seg, str) and isinstance(current, dict):
                current = current.get(seg)
            else:
                return None
        return current

    return None


def resolve_template(value: dict[str, Any], state: dict[str, Any], locals_map: dict[str, Any] | None = None) -> str:
    """Resolve a template FlowValue by substituting ``{{ref}}`` placeholders.

    Placeholder syntax is ``{{nodeId__field}}`` (the flat data-channel key).
    Missing refs are substituted with empty string.
    """
    content = value.get("content")
    if not isinstance(content, str):
        return ""

    data = state.get(DATA_KEY, {})

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        parts = key.split(".")
        head_key = parts[0]

        # Loop-locals form: {{loopId_locals.item}} or {{loopId_locals.item.sub}}
        # → locals_map['item'], then drill into ['sub'] if nested.
        if head_key.endswith("_locals"):
            # Recover locals from state if not passed (loop body nodes case).
            lm = locals_map if locals_map is not None else _locals_from_state(state, head_key)
            if lm is None:
                return ""
            if len(parts) < 2:
                return ""
            current: Any = lm.get(parts[1])
            for seg in parts[2:]:
                if isinstance(current, dict):
                    current = current.get(seg)
                else:
                    current = ""
                    break
            return "" if current is None else str(current)

        # Standard data-channel field: {{nodeId__field}} or {{nodeId__field.sub}}
        current: Any = data.get(head_key)
        for seg in parts[1:]:
            if isinstance(current, dict):
                current = current.get(seg)
            else:
                current = ""
                break
        return "" if current is None else str(current)

    return _TEMPLATE_PATTERN.sub(_sub, content)


def resolve_flow_value(
    value: dict[str, Any] | None,
    state: dict[str, Any],
    locals_map: dict[str, Any] | None = None,
) -> Any:
    """Resolve any FlowValue (constant/ref/template) into a concrete value.

    - None/missing → None
    - constant → content
    - ref → resolve_ref
    - template → resolve_template (always a string)
    - anything else → returned as-is (defensive)
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        return value
    vtype = value.get("type")
    if vtype == "constant":
        return value.get("content")
    if vtype == "ref":
        return resolve_ref(value, state, locals_map)
    if vtype == "template":
        return resolve_template(value, state, locals_map)
    return value.get("content", value)


def resolve_inputs_values(
    inputs_values: dict[str, Any] | None,
    state: dict[str, Any],
    locals_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a node's ``data.inputsValues`` dict into concrete key→value pairs."""
    if not inputs_values:
        return {}
    return {
        key: resolve_flow_value(val, state, locals_map)
        for key, val in inputs_values.items()
    }
