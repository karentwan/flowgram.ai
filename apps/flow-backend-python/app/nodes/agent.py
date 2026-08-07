"""Agent node executor — mirrors Node's AgentExecutor (/chat/process POST).

Calls an agent server endpoint (e.g. ``https://host/chat/process``) in
non-streaming mode and extracts the assistant's reply. The protocol matches
Node exactly so the two backends are interchangeable for the same agent server.

Body: ``{input, session_id, user_id, agent_id, stream: false}``
Response: an OpenAI Responses-shaped object; we extract message text or
concatenate function_call_output texts as a fallback.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.engine.values import resolve_flow_value, resolve_inputs_values
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode


def make_agent_node(node: WorkflowNode) -> NodeFn:
    """Build an async node fn that calls an agent's /chat/process endpoint."""
    data = node.data
    server = data.get("server") or {}
    headers_values = server.get("headersValues") or {}
    agent_id = data.get("agentId") or ""
    user_id = data.get("userId") or ""
    input_value = data.get("input") or {}
    session_cfg = data.get("session") or {}
    timeout_cfg = data.get("timeout") or {}

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        url = server.get("url") or ""
        if not url:
            raise ValueError("Agent server.url is required")
        if not agent_id:
            raise ValueError("Agent agentId is required")
        if not user_id:
            raise ValueError("Agent userId is required")

        # Resolve templated input (may reference upstream variables).
        input_text = resolve_flow_value(input_value, state)
        if not input_text:
            raise ValueError("Agent input is required")

        # Resolve headers (secrets already decrypted upstream).
        headers = {
            k: str(resolve_flow_value(v, state) or "")
            for k, v in headers_values.items()
        }

        # session_id: auto-generate per run, or use fixed id.
        if session_cfg.get("auto", True):
            session_id = f"agent_{uuid.uuid4()}"
        else:
            session_id = session_cfg.get("id", "")
        if not session_id:
            raise ValueError("Agent sessionId is required")

        timeout_ms = int(timeout_cfg.get("timeout", 120000) or 120000)
        response = await _call_agent(url, headers, agent_id, user_id, session_id, str(input_text), timeout_ms)

        status = response.get("status")
        if status != "completed":
            err = (response.get("error") or {}).get("message", f"agent run status: {status}")
            raise RuntimeError(f"Agent call failed: {err}")

        reply = _extract_reply(response)
        return outputs_for(node, {"reply": reply, "usage": response.get("usage")})

    return wrap_with_status(node.id, fn)


async def _call_agent(
    url: str,
    headers: dict[str, str],
    agent_id: str,
    user_id: str,
    session_id: str,
    input_text: str,
    timeout_ms: int,
) -> dict[str, Any]:
    """POST to the agent's chat endpoint (non-streaming)."""
    rpc_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **headers,
    }
    body = {
        "input": input_text,
        "session_id": session_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "stream": False,
    }
    timeout = timeout_ms / 1000
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=rpc_headers, json=body)
    if resp.status_code >= 400:
        raise RuntimeError(f"Agent server responded with status {resp.status_code}")
    return resp.json()


def _extract_reply(response: dict[str, Any]) -> str:
    """Extract the assistant's text reply (message content, fallback to outputs)."""
    items = response.get("output") or []

    # Primary: message content blocks.
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if isinstance(block, dict):
                text = block.get("text") or ""
                if text:
                    parts.append(text)
    if parts:
        return "\n\n".join(parts)

    # Fallback: concatenate non-empty function_call_output texts.
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("type") == "function_call_output"
            and isinstance(item.get("output"), str)
            and item["output"]
        ):
            parts.append(item["output"])
    return "\n\n".join(parts)
