"""Code node executor — runs user Python via exec() (dev only).

Grill decision (contract §2): code nodes run Python only. The Node backend
ran JS in a QuickJS sandbox; the Python backend redefines this as Python exec.

SECURITY: this is the dev implementation — it uses bare ``exec`` with NO
sandboxing. Production must add process/container isolation (grill marked this
as a follow-up). The canvas still surfaces a code editor; Python syntax is
expected.

The node payload is ``data.script`` (``{ language, content }``). The user code
must define ``def main(params):`` returning a dict of outputs; inputs come from
``inputsValues`` resolved to ``params``. ``language: python`` runs as-is; any
other language raises a clear error because the Python backend has no JS
runtime.
"""

from __future__ import annotations

from typing import Any

from app.engine.values import resolve_inputs_values
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode

PYTHON_LANGUAGE = "python"


def _resolve_code(node: WorkflowNode) -> tuple[str, str]:
    """Return ``(code, language)`` from ``data.script``."""
    script = node.data.get("script")
    if isinstance(script, dict):
        language = str(script.get("language") or PYTHON_LANGUAGE)
        content = script.get("content")
        if isinstance(content, str) and content.strip():
            return content, language
        return "", language

    return "", PYTHON_LANGUAGE


def make_code_node(node: WorkflowNode) -> NodeFn:
    """Build a node fn that execs user Python defining ``main(params)``."""
    code, language = _resolve_code(node)
    inputs_values = node.data.get("inputsValues") or {}

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        params = resolve_inputs_values(inputs_values, state)
        if language != PYTHON_LANGUAGE:
            raise RuntimeError(
                f"Code node {node.id} uses language '{language}', which the Python backend "
                "cannot execute (no JS runtime). Rewrite the node as Python "
                "(`def main(params):` returning a dict), or run the workflow on the Node "
                "backend (QuickJS) to execute JavaScript."
            )
        # Execute user code in a fresh namespace; expect a main(params) function.
        namespace: dict[str, Any] = {}
        try:
            exec(compile(code, f"<node {node.id}>", "exec"), namespace)  # noqa: S102
        except Exception as e:
            raise RuntimeError(f"Code node {node.id} failed to compile: {e}") from e
        main_fn = namespace.get("main")
        if not callable(main_fn):
            raise RuntimeError(
                f"Code node {node.id} must define a `def main(params):` function"
            )
        try:
            result = main_fn(params)
        except Exception as e:
            raise RuntimeError(f"Code node {node.id} main() raised: {e}") from e
        if not isinstance(result, dict):
            result = {"result": result}
        return outputs_for(node, result)

    return wrap_with_status(node.id, node.type, fn)
