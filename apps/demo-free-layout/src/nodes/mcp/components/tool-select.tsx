/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useEffect, useMemo, useState } from 'react';

import { Field, useWatch } from '@flowgram.ai/free-layout-editor';
import { Select } from '@douyinfe/semi-ui';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

interface MCPTool {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

interface JsonRpcResponse<P> {
  result?: P;
  error?: { message?: string };
}

/**
 * A flow-value header entry under server.headersValues. Only `constant`
 * entries carry a literal header value in the browser; ref/template entries
 * reference upstream variables that can only be resolved at runtime.
 */
interface HeaderValue {
  type?: string;
  content?: unknown;
}

/**
 * Reduce headersValues (flow values) to a plain string map for the discovery
 * request. Only constant entries are included — ref/template entries cannot
 * be resolved in the browser (no variable store at design time).
 */
function headersValuesToStringMap(values?: Record<string, HeaderValue>): Record<string, string> {
  if (!values) return {};
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(values)) {
    if (value?.type === 'constant' && typeof value.content === 'string') {
      out[key] = value.content;
    }
  }
  return out;
}

/**
 * Calls the MCP server's `tools/list` JSON-RPC method to discover available
 * tools at design time. Mirrors what the runtime executor does for `tools/call`:
 * a plain `fetch` POST — no MCP SDK client.
 *
 * The server URL and headers are read inline from the node form (no registry).
 * This runs in the browser, so servers must be CORS-enabled (or reachable from
 * the editor origin). If discovery fails, the user can still type a tool name
 * manually via the Select's `allowCreate`.
 */
async function listTools(url: string, headers?: Record<string, string>): Promise<MCPTool[]> {
  if (!url) {
    return [];
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      ...(headers || {}),
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/list',
    }),
  });
  if (!response.ok) {
    throw new Error(`MCP server responded with status ${response.status}`);
  }
  const contentType = response.headers.get('content-type') || '';
  const text = await response.text();
  let payload: JsonRpcResponse<{ tools?: MCPTool[] }> | undefined;

  if (contentType.includes('text/event-stream')) {
    // Pick the last `data:` JSON chunk from the SSE stream.
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data:')) {
        try {
          payload = JSON.parse(trimmed.slice(5).trim());
        } catch {
          // ignore malformed chunk
        }
      }
    }
  } else {
    payload = JSON.parse(text);
  }

  if (payload?.error) {
    throw new Error(`MCP JSON-RPC error: ${payload.error.message ?? 'unknown'}`);
  }
  return payload?.result?.tools ?? [];
}

export function ToolSelect() {
  const { readonly } = useNodeRenderContext();
  const url = useWatch<string>('server.url') ?? '';
  const headersValues = useWatch<Record<string, HeaderValue>>('server.headersValues');
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Re-discover whenever the server URL or headers change. Serialize headers so
  // the effect dependency is stable across renders with the same content.
  const headersKey = JSON.stringify(headersValues || {});

  useEffect(() => {
    setTools([]);
    setError('');
    if (!url) {
      return;
    }
    setLoading(true);
    // Only constant header values are resolvable in the browser; ref/template
    // entries (which reference upstream variables) are skipped here.
    listTools(url, headersValuesToStringMap(headersValues))
      .then((result) => setTools(result))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [url, headersKey]);

  const optionList = useMemo(
    () => tools.map((tool) => ({ label: tool.name, value: tool.name })),
    [tools]
  );

  const placeholder = !url
    ? 'Enter a server URL first'
    : error
    ? `Discovery failed: ${error}`
    : loading
    ? 'Loading tools...'
    : 'Select a tool';

  return (
    <FormItem name="Tool" required vertical type="string">
      <Field<string> name="toolName" defaultValue="">
        {({ field }) => (
          <Select
            value={field.value}
            onChange={(value) => field.onChange(value as string)}
            style={{ width: '100%' }}
            size="small"
            disabled={readonly || !url}
            loading={loading}
            placeholder={placeholder}
            optionList={optionList}
            filter
            // Allow manual entry as a fallback when discovery fails.
            allowCreate
          />
        )}
      </Field>
    </FormItem>
  );
}
