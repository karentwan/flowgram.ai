/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import {
  ExecutionContext,
  ExecutionResult,
  FlowGramNode,
  INode,
  INodeExecutor,
  MCPNodeSchema,
} from '@flowgram.ai/runtime-interface';

/**
 * Minimal JSON-RPC 2.0 request envelope used for the MCP Streamable-HTTP
 * transport. We send these via plain `fetch` — no MCP SDK client is involved.
 */
interface JsonRpcRequest<P = unknown> {
  jsonrpc: '2.0';
  id: number | string;
  method: string;
  params?: P;
}

/**
 * Shape of a successful `tools/call` result per the MCP spec.
 * `content` is always present; `isError` and `structuredContent` are optional.
 */
interface CallToolResult {
  content: Array<{ type: string; [key: string]: unknown }>;
  isError?: boolean;
  structuredContent?: unknown;
}

export interface MCPExecutorInputs {
  serverUrl: string;
  serverHeaders: Record<string, string>;
  toolName: string;
  args: Record<string, unknown>;
  retryTimes: number;
  timeout: number;
}

export class MCPExecutor implements INodeExecutor {
  public readonly type = FlowGramNode.MCP;

  public async execute(context: ExecutionContext): Promise<ExecutionResult> {
    const inputs = this.parseInputs(context);
    const result = await this.callTool(inputs);

    // Return the full CallToolResult envelope. The node's declared `outputs`
    // schema (default: { content, isError, structuredContent }) governs which
    // fields downstream variables can reference. `isError` stays available for
    // error checking; structuredContent carries the tool-specific payload.
    return {
      outputs: {
        content: result.content,
        isError: result.isError ?? false,
        structuredContent: result.structuredContent,
      },
    };
  }

  private async callTool(inputs: MCPExecutorInputs): Promise<CallToolResult> {
    const { serverUrl, serverHeaders, toolName, args, retryTimes, timeout } = inputs;

    const requestBody: JsonRpcRequest<{ name: string; arguments: Record<string, unknown> }> = {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: { name: toolName, arguments: args },
    };

    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= retryTimes; attempt++) {
      try {
        const response = await fetch(serverUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json, text/event-stream',
            ...serverHeaders,
          },
          body: JSON.stringify(requestBody),
          signal: AbortSignal.timeout(timeout),
        });

        if (!response.ok) {
          throw new Error(`MCP server responded with status ${response.status}`);
        }

        return await this.parseResponse(response);
      } catch (error) {
        lastError = error as Error;
        if (attempt < retryTimes) {
          // Exponential backoff, mirroring HTTPExecutor.
          await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      }
    }
    throw lastError || new Error('MCP tools/call failed after all retry attempts');
  }

  /**
   * Parse the JSON-RPC response. Streamable-HTTP servers may answer with either
   * a single JSON object or an SSE stream of `data:` lines — handle both.
   */
  private async parseResponse(response: Response): Promise<CallToolResult> {
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();

    // SSE-style response: extract the last `data:` JSON payload.
    if (contentType.includes('text/event-stream')) {
      const lines = text.split('\n');
      let lastData: unknown = undefined;
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:')) {
          try {
            lastData = JSON.parse(trimmed.slice(5).trim());
          } catch {
            // ignore malformed chunk
          }
        }
      }
      return this.extractResult(lastData);
    }

    // Plain JSON response.
    return this.extractResult(JSON.parse(text));
  }

  private extractResult(payload: unknown): CallToolResult {
    const rpc = payload as { result?: CallToolResult; error?: { message?: string } };
    if (rpc.error) {
      throw new Error(`MCP JSON-RPC error: ${rpc.error.message ?? 'unknown error'}`);
    }
    if (!rpc.result) {
      throw new Error('MCP JSON-RPC response missing result');
    }
    return rpc.result;
  }

  private parseInputs(context: ExecutionContext): MCPExecutorInputs {
    const mcpNode = context.node as INode<MCPNodeSchema['data']>;
    const server = mcpNode.data.server;
    if (!server?.url) {
      throw new Error('MCP server url is required');
    }

    const toolName = mcpNode.data.toolName;
    if (!toolName) {
      throw new Error('MCP toolName is required');
    }

    const args = context.runtime.state.parseInputs({
      values: mcpNode.data.argsValues,
      declare: mcpNode.data.args,
    });

    // Resolve header flow values (constant/ref/template) into plain strings,
    // mirroring how the HTTP node parses its headersValues.
    const serverHeaders = context.runtime.state.parseInputs({
      values: server.headersValues,
      declare: server.headers,
    });

    const inputs: MCPExecutorInputs = {
      serverUrl: server.url,
      serverHeaders,
      toolName,
      args,
      retryTimes: mcpNode.data.timeout.retryTimes,
      timeout: mcpNode.data.timeout.timeout,
    };
    context.snapshot.update({
      inputs: JSON.parse(JSON.stringify(inputs)),
    });
    return inputs;
  }
}
