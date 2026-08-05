/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IFlowConstantRefValue } from '@schema/value';
import { WorkflowNodeSchema } from '@schema/node';
import { IJsonSchema } from '@schema/json-schema';
import { FlowGramNode } from '@node/constant';

interface MCPNodeData {
  title: string;
  outputs: IJsonSchema<'object'>;
  /**
   * Inline MCP server connection config. The node is self-contained — no
   * external server registry. Secrets here are serialized with the workflow
   * JSON (same trade-off as the HTTP node's `api`/`headers`).
   */
  server: {
    /** Base URL of the HTTP MCP endpoint (Streamable-HTTP transport). */
    url: string;
    /**
     * Inferred object schema for the request headers — derived from
     * `headersValues` by the createInferInputsPlugin on the editor side
     * (same pattern as the HTTP node's headers/headersValues).
     */
    headers: IJsonSchema<'object'>;
    /**
     * User-filled request headers as flow values (constant / ref / template).
     * Secrets here are serialized with the workflow JSON (encrypted at rest
     * by flow-backend's secrets module, see server.headersValues.constant).
     */
    headersValues: Record<string, IFlowConstantRefValue>;
  };
  /**
   * The MCP tool to call (resolved at design time via tools/list).
   */
  toolName: string;
  /**
   * Inferred input schema for the tool arguments, derived from argsValues
   * via the createInferInputsPlugin on the editor side.
   */
  args: IJsonSchema<'object'>;
  /**
   * User-filled tool arguments as flow values (constant / ref / template).
   */
  argsValues: Record<string, IFlowConstantRefValue>;
  timeout: {
    retryTimes: number;
    timeout: number;
  };
}
export type MCPNodeSchema = WorkflowNodeSchema<FlowGramNode.MCP, MCPNodeData>;
