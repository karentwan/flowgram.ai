/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { v4 as uuidv4 } from 'uuid';
import {
  ExecutionContext,
  ExecutionResult,
  FlowGramNode,
  INode,
  INodeExecutor,
  AgentNodeSchema,
} from '@flowgram.ai/runtime-interface';

/**
 * Minimal subset of the OpenAI Responses object returned by the agent's
 * `/chat/process` endpoint in non-streaming mode (stream:false).
 *
 * `output[]` is an ordered list of items; we only need message items to extract
 * the assistant's reply text. Other item types (reasoning, function_call, ...)
 * are ignored for the MVP — they remain in the raw response for observability.
 */
interface ResponsesMessageContent {
  type: string;
  text?: string;
}
interface ResponsesOutputItem {
  type: string;
  // message items carry content blocks with text
  content?: ResponsesMessageContent[];
  // function_call items carry the tool name + call id
  name?: string;
  call_id?: string;
  // function_call_output items carry the result text directly in `output`,
  // linked back to the call via call_id
  output?: string;
}
interface ResponsesObject {
  id?: string;
  status?: string;
  output?: ResponsesOutputItem[];
  error?: { message?: string };
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
}

export interface AgentExecutorInputs {
  serverUrl: string;
  serverHeaders: Record<string, string>;
  agentId: string;
  userId: string;
  sessionId: string;
  input: string;
  timeout: number;
}

export class AgentExecutor implements INodeExecutor {
  public readonly type = FlowGramNode.Agent;

  public async execute(context: ExecutionContext): Promise<ExecutionResult> {
    const inputs = this.parseInputs(context);
    const response = await this.callAgent(inputs);

    if (response.status !== 'completed') {
      const message = response.error?.message || `agent run status: ${response.status}`;
      throw new Error(`Agent call failed: ${message}`);
    }

    // Extract the agent's text reply. Prefer message.content text; if empty
    // (some agent servers put everything in function_call_output), concatenate
    // ALL non-empty function_call_output texts so no part of the reply is lost.
    const items = response.output || [];

    // Try message content first (the agent's direct text output).
    let reply = items
      .filter((item) => item.type === 'message' && Array.isArray(item.content))
      .flatMap((item) => item.content || [])
      .map((block) => block.text || '')
      .filter((text) => text.length > 0)
      .join('\n\n');

    // Fallback: concatenate all non-empty function_call_output texts.
    if (!reply) {
      reply = items
        .filter(
          (item) =>
            item.type === 'function_call_output' &&
            typeof item.output === 'string' &&
            item.output.length > 0
        )
        .map((item) => item.output as string)
        .join('\n\n');
    }

    return {
      outputs: {
        reply,
        usage: response.usage,
      },
    };
  }

  private async callAgent(inputs: AgentExecutorInputs): Promise<ResponsesObject> {
    const { serverUrl, serverHeaders, agentId, userId, sessionId, input } = inputs;

    const response = await fetch(serverUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...serverHeaders,
      },
      body: JSON.stringify({
        input,
        session_id: sessionId,
        user_id: userId,
        agent_id: agentId,
        // MVP uses the non-streaming path: a single JSON Responses object is
        // returned once the run completes. SSE streaming can be added later.
        stream: false,
      }),
      signal: AbortSignal.timeout(inputs.timeout),
    });

    if (!response.ok) {
      throw new Error(`Agent server responded with status ${response.status}`);
    }
    return (await response.json()) as ResponsesObject;
  }

  private parseInputs(context: ExecutionContext): AgentExecutorInputs {
    const agentNode = context.node as INode<AgentNodeSchema['data']>;
    const server = agentNode.data.server;
    if (!server?.url) {
      throw new Error('Agent server url is required');
    }
    if (!agentNode.data.agentId) {
      throw new Error('Agent agentId is required');
    }
    if (!agentNode.data.userId) {
      throw new Error('Agent userId is required');
    }

    // Resolve the templated input (may reference upstream variables).
    const inputVariable = context.runtime.state.parseTemplate(agentNode.data.input);
    if (!inputVariable) {
      throw new Error('Agent input is required');
    }

    // Resolve header flow values (constant/ref/template) into plain strings,
    // mirroring how the HTTP node parses its headersValues.
    const serverHeaders = context.runtime.state.parseInputs({
      values: server.headersValues,
      declare: server.headers,
    });

    // session_id: auto-generate per run for a fresh conversation, or use the
    // fixed id verbatim to continue an existing one.
    const sessionId = agentNode.data.session.auto ? `agent_${uuidv4()}` : agentNode.data.session.id;
    if (!sessionId) {
      throw new Error('Agent sessionId is required');
    }

    const inputs: AgentExecutorInputs = {
      serverUrl: server.url,
      serverHeaders,
      agentId: agentNode.data.agentId,
      userId: agentNode.data.userId,
      sessionId,
      input: inputVariable.value,
      // Fall back to 120s when the field isn't set (older saved nodes).
      timeout: agentNode.data.timeout?.timeout ?? 120000,
    };
    context.snapshot.update({
      inputs: JSON.parse(JSON.stringify(inputs)),
    });
    return inputs;
  }
}
