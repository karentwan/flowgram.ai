"""Condition node: routes to branches via LangGraph conditional edges.

A condition node declares ``data.conditions: [{key, value:{left,operator,right}}]``.
At runtime we evaluate each condition against the State and return the ``key``
of the first matching branch; the loader wires that key to the target node via
``add_conditional_edges``.

The condition node itself is a pass-through (no outputs); its only job is the
routing function exposed via ``make_condition_router``.
"""

from __future__ import annotations

from typing import Any

from app.engine.values import resolve_flow_value
from app.schemas.ir import WorkflowNode

# Operator → Python predicate. Mirrors ConditionOperator enum.
import operator as _op

_OPS = {
    "eq": _op.eq,
    "neq": _op.ne,
    "gt": _op.gt,
    "gte": _op.ge,
    "lt": _op.lt,
    "lte": _op.le,
}


def _to_number(v: Any) -> float | None:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _evaluate_one(left: Any, op: str, right: Any) -> bool:
    """Evaluate a single condition. Mirrors Node's condition semantics."""
    if op in ("is_empty",):
        return left is None or left == "" or (isinstance(left, (list, dict)) and len(left) == 0)
    if op in ("is_not_empty",):
        return not (left is None or left == "" or (isinstance(left, (list, dict)) and len(left) == 0))
    if op in ("is_true",):
        return bool(left) is True
    if op in ("is_false",):
        return bool(left) is False
    if op in ("contains",):
        try:
            return right in left  # type: ignore[operator]
        except TypeError:
            return False
    if op in ("not_contains",):
        try:
            return right not in left  # type: ignore[operator]
        except TypeError:
            return True
    if op in ("in",):
        try:
            return left in right  # type: ignore[operator]
        except TypeError:
            return False
    if op in ("nin",):
        try:
            return left not in right  # type: ignore[operator]
        except TypeError:
            return True
    # Comparison ops need numeric coercion for strings.
    if op in _OPS:
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return _OPS[op](left, right)  # type: ignore[operator]
        ln, rn = _to_number(left), _to_number(right)
        if ln is not None and rn is not None:
            return _OPS[op](ln, rn)  # type: ignore[operator]
        # Fall back to direct comparison for eq/neq on non-numeric.
        if op == "eq":
            return left == right
        if op == "neq":
            return left != right
        return False
    return False


def make_condition_router(node: WorkflowNode):
    """Return a routing function for ``add_conditional_edges``.

    The function evaluates the node's conditions in order and returns the first
    matching ``key``. Callers map keys→target node ids.
    """
    conditions = node.data.get("conditions") or []

    def router(state: dict[str, Any]) -> str:
        for cond in conditions:
            value = cond.get("value") or {}
            left = resolve_flow_value(value.get("left"), state)
            op = value.get("operator")
            right = resolve_flow_value(value.get("right"), state)
            if _evaluate_one(left, op, right):
                return cond.get("key")
        # No match: return empty string; loader maps "" to END (or the first edge).
        return ""

    return router
