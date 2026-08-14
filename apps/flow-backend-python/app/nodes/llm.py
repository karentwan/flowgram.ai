"""LLM node executor — calls a chat model via langchain-openai.

Mirrors Node's LLMExecutor (@langchain/openai ChatOpenAI). Resolves
modelName/apiKey/apiHost/temperature/systemPrompt/prompt from inputsValues,
invokes ChatOpenAI, and writes ``result`` (the assistant message content) to
outputs.
"""

from __future__ import annotations

from typing import Any

from app.engine.values import resolve_inputs_values
from app.nodes.base import NodeFn, outputs_for, wrap_with_status
from app.schemas.ir import WorkflowNode


def make_llm_node(node: WorkflowNode) -> NodeFn:
    """Build an async LangGraph node fn that calls a chat model."""
    inputs_values = (node.data.get("inputsValues") or node.data.get("inputValues") or {})

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        # Late import keeps the dependency optional for non-LLM tests.
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        params = resolve_inputs_values(inputs_values, state)
        model_name = params.get("modelName") or "gpt-4o-mini"
        api_key = params.get("apiKey") or ""
        api_host = params.get("apiHost") or None
        temperature = params.get("temperature")
        system_prompt = params.get("systemPrompt")
        prompt = params.get("prompt") or ""

        kwargs: dict[str, Any] = {"model": model_name, "api_key": api_key}
        if api_host:
            kwargs["base_url"] = api_host
        if temperature is not None:
            try:
                kwargs["temperature"] = float(temperature)
            except (TypeError, ValueError):
                pass

        model = ChatOpenAI(**kwargs)
        messages: list[Any] = []
        if system_prompt:
            messages.append(SystemMessage(content=str(system_prompt)))
        messages.append(HumanMessage(content=str(prompt)))

        response = await model.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        # Some providers return list content (multi-modal); coerce to string.
        if not isinstance(content, str):
            content = str(content)
        return outputs_for(node, {"result": content})

    return wrap_with_status(node, fn)
