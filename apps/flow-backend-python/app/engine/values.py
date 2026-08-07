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

# Matches {{ path }} in template strings.
_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([\w]+(?:\.[\w]+)*)\s*\}\}")


def resolve_ref(value: dict[str, Any], state: dict[str, Any], locals_map: dict[str, Any] | None = None) -> Any:
    """Resolve a ref FlowValue (``{type:'ref', content: [path...]}``).

    Returns the referenced value, or None if unresolved.
    """
    path = value.get("content") or []
    if not isinstance(path, list) or not path:
        return None

    head = path[0]

    # Loop-locals scope (e.g. ['loop_0_locals', 'item']).
    if isinstance(head, str) and head.endswith("_locals"):
        if locals_map is None:
            return None
        if len(path) < 2:
            return None
        return locals_map.get(path[1])

    # Standard node ref: ['nodeId', 'field', ...nested?]
    if len(path) >= 2 and isinstance(head, str) and isinstance(path[1], str):
        data = state.get(DATA_KEY, {})
        field_key = f"{head}__{path[1]}"
        current: Any = data.get(field_key)
        if current is None:
            # Fall back to inputs dict if the start node hasn't run yet.
            current = get_inputs(state).get(path[1])
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

        # Loop-locals form: {{loop_0_locals.item}} → locals_map['item']
        if locals_map is not None and head_key.endswith("_locals"):
            local_name = parts[-1] if len(parts) > 1 else parts[0]
            return str(locals_map.get(local_name, ""))

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
