/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IFlowConstantRefValue, IFlowTemplateValue } from '@schema/value';
import { WorkflowNodeSchema } from '@schema/node';
import { IJsonSchema } from '@schema/json-schema';
import { FlowGramNode } from '@node/constant';

interface AgentNodeData {
  title: string;
  outputs: IJsonSchema<'object'>;
  /**
   * Inline agent server connection config. The node is self-contained — no
   * external registry. `url` is the full endpoint (e.g.
   * `https://host/chat/process`). Secrets here are serialized with the
   * workflow JSON (same trade-off as the HTTP/MCP nodes).
   */
  server: {
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
   * The agent template to run (→ body.agent_id).
   */
  agentId: string;
  /**
   * Caller identity (→ body.user_id). Free-form string.
   */
  userId: string;
  /**
   * The user message for this turn (→ body.input). Template values can
   * reference upstream variables. Conversation history lives server-side,
   * keyed by sessionId, so only the new message is sent each turn.
   */
  input: IFlowTemplateValue;
  /**
   * Session/conversation id handling (→ body.session_id).
   *   auto=true  → a fresh id is generated per workflow run (new conversation)
   *   auto=false → use `id` verbatim (continue a fixed conversation)
   */
  session: {
    auto: boolean;
    id: string;
  };
}
export type AgentNodeSchema = WorkflowNodeSchema<FlowGramNode.Agent, AgentNodeData>;
