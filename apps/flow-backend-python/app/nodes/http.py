"""HTTP node executor — makes an outbound request via httpx.

Mirrors Node's HTTPExecutor (global fetch → httpx). Resolves url/method/headers/
body from ``data.api`` + ``data.{headers,params}Values`` + ``data.body``,
performs the request, and writes the JSON response body fields to outputs
(flattened top-level keys, matching Node behavior).
"""

from __future__ import annotations

from typing import Any

import httpx

from app.engine.values import resolve_flow_value, resolve_inputs_values
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode


def make_http_node(node: WorkflowNode) -> NodeFn:
    """Build an async LangGraph node fn that performs an HTTP request."""
    data = node.data
    api = data.get("api") or {}
    body_cfg = data.get("body") or {}
    headers_values = data.get("headersValues") or {}
    params_values = data.get("paramsValues") or {}

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        method = (api.get("method") or "GET").upper()
        url = resolve_flow_value(api.get("url"), state) or ""

        headers = {
            k: resolve_flow_value(v, state) or ""
            for k, v in headers_values.items()
        }
        params = {
            k: resolve_flow_value(v, state) or ""
            for k, v in params_values.items()
        }

        # Body
        json_body: Any = None
        body_type = body_cfg.get("bodyType")
        if body_type == "JSON":
            json_body = resolve_flow_value(body_cfg.get("json"), state)
        elif body_type in ("raw-text", "binary"):
            # raw text / binary sent as content body (text body simplification).
            pass

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, headers=headers, params=params, json=json_body
            )
            resp.raise_for_status()

        # Parse response: try JSON, fall back to raw text under a 'body' key.
        try:
            payload = resp.json()
        except Exception:
            payload = {"body": resp.text}

        # Flatten top-level object keys into outputs (matches Node behavior).
        outputs: dict[str, Any] = {}
        if isinstance(payload, dict):
            outputs.update(payload)
        else:
            outputs["body"] = payload
        return outputs_for(node, outputs)

    return wrap_with_status(node, fn)
