"""Template value resolution tests.

Covers the canvas-native dot form ({{nodeId.field}}) alongside the flat
({{nodeId__field}}) form the Python state channel uses, plus loop-locals
templates. Regression guard for the editor/Python syntax mismatch.
"""

from __future__ import annotations

from app.engine.values import resolve_template


def _state(**fields: object) -> dict:
    return {"data": fields}


def test_flat_form() -> None:
    state = _state(llm_0__result="flat-ok")
    assert (
        resolve_template({"type": "template", "content": "r={{llm_0__result}}"}, state)
        == "r=flat-ok"
    )


def test_dot_form_canvas_native() -> None:
    state = _state(code_json_0__email_json='{"a":1}')
    assert (
        resolve_template({"type": "template", "content": "x{{code_json_0.email_json}}y"}, state)
        == 'x{"a":1}y'
    )


def test_dot_form_nested_tail() -> None:
    state = _state(http_0__body={"name": "n1"})
    assert resolve_template({"type": "template", "content": "{{http_0.body.name}}"}, state) == "n1"


def test_flat_form_nested_tail() -> None:
    state = _state(http_0__body={"name": "n1"})
    assert resolve_template({"type": "template", "content": "{{http_0__body.name}}"}, state) == "n1"


def test_missing_ref_becomes_empty() -> None:
    state = _state(other__x="1")
    assert resolve_template({"type": "template", "content": "[{{nope.missing}}]"}, state) == "[]"


def test_loop_locals_template() -> None:
    state = {"data": {}, "__loop_locals__": {"loop_0": {"item": {"name": "it1"}, "index": 2}}}
    assert (
        resolve_template(
            {"type": "template", "content": "{{loop_0_locals.item.name}}#{{loop_0_locals.index}}"},
            state,
        )
        == "it1#2"
    )
