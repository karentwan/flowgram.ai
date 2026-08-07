"""MCP node executor — mirrors Node's MCPExecutor (JSON-RPC over fetch).

Despite the grill note about langchain-mcp-adapters, the Node backend uses a
hand-written JSON-RPC client (no SDK). To preserve byte-identical behavior and
secrets-decryption reuse, the Python side mirrors that protocol directly:
  - POST a JSON-RPC 2.0 ``tools/call`` envelope to ``server.url``
  - Accept either a single JSON response or an SSE stream (last data: payload)
  - Retry with exponential backoff (``retryTimes``)
  - Flatten structuredContent top-level keys into outputs (matches Node)

Secrets in ``server.headersValues.{*}.content`` are decrypted by the
secrets-traversal layer before reaching the executor; here we just resolve
them as flow values.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.engine.values import resolve_flow_value, resolve_inputs_values
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode


def make_mcp_node(node: WorkflowNode) -> NodeFn:
    """Build an async node fn that calls an MCP tool via JSON-RPC."""
    data = node.data
    server = data.get("server") or {}
    headers_values = server.get("headersValues") or {}
    args_values = data.get("argsValues") or {}
    tool_name = data.get("toolName") or ""
    timeout_cfg = data.get("timeout") or {}

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        url = server.get("url") or ""
        if not url:
            raise ValueError("MCP server.url is required")
        if not tool_name:
            raise ValueError("MCP toolName is required")

        # Resolve headers and args (secrets already decrypted upstream).
        headers = {
            k: str(resolve_flow_value(v, state) or "")
            for k, v in headers_values.items()
        }
        args = resolve_inputs_values(args_values, state)

        retry_times = int(timeout_cfg.get("retryTimes", 0) or 0)
        timeout_ms = int(timeout_cfg.get("timeout", 30000) or 30000)

        result = await _call_tool_with_retry(
            url, headers, tool_name, args, retry_times, timeout_ms
        )
        outputs = _build_outputs(result)
        return outputs_for(node, outputs)

    return wrap_with_status(node.id, node.type, fn)


async def _call_tool_with_retry(
    url: str,
    headers: dict[str, str],
    tool_name: str,
    args: dict[str, Any],
    retry_times: int,
    timeout_ms: int,
) -> dict[str, Any]:
    """Send tools/call JSON-RPC, retry on failure with exponential backoff."""
    request_body = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args},
    }
    rpc_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **headers,
    }
    timeout = timeout_ms / 1000
    last_error: Exception | None = None

    for attempt in range(retry_times + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=rpc_headers, json=request_body)
            if resp.status_code >= 400:
                raise RuntimeError(f"MCP server responded with status {resp.status_code}")
            return _parse_response(resp)
        except Exception as e:
            last_error = e
            if attempt < retry_times:
                await _sleep(2**attempt)

    raise last_error or RuntimeError("MCP tools/call failed after all retries")


def _parse_response(resp: httpx.Response) -> dict[str, Any]:
    """Parse JSON-RPC result from either a JSON body or an SSE stream."""
    content_type = resp.headers.get("content-type", "")
    text = resp.text

    if "text/event-stream" in content_type:
        # SSE: extract the last `data:` JSON payload.
        last_data: Any = None
        for line in text.split("\n"):
            trimmed = line.strip()
            if trimmed.startswith("data:"):
                payload = trimmed[5:].strip()
                try:
                    last_data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
        return _extract_result(last_data)

    return _extract_result(json.loads(text))


def _extract_result(payload: Any) -> dict[str, Any]:
    """Unwrap the JSON-RPC ``{result, error}`` envelope."""
    if not isinstance(payload, dict):
        raise RuntimeError("MCP JSON-RPC response is not an object")
    if payload.get("error"):
        msg = (payload["error"] or {}).get("message", "unknown error")
        raise RuntimeError(f"MCP JSON-RPC error: {msg}")
    result = payload.get("result")
    if result is None:
        raise RuntimeError("MCP JSON-RPC response missing result")
    return result


def _build_outputs(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten structuredContent into top-level outputs (matches Node)."""
    content = result.get("content") or []
    is_error = result.get("isError", False)
    structured = result.get("structuredContent")

    # Fallback: parse structuredContent out of the first text content block.
    if structured is None:
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str) and text:
                    try:
                        structured = json.loads(text)
                    except json.JSONDecodeError:
                        pass
                break

    outputs: dict[str, Any] = {
        "content": content,
        "isError": is_error,
        "structuredContent": structured,
    }
    # Flatten structured top-level keys (don't clobber reserved keys).
    if isinstance(structured, dict):
        for key, value in structured.items():
            if key not in outputs:
                outputs[key] = value
    return outputs


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
