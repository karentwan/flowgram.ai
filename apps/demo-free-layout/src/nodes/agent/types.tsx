/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IFlowConstantRefValue, IFlowTemplateValue } from '@flowgram.ai/runtime-interface';
import { FlowNodeJSON } from '@flowgram.ai/free-layout-editor';
import { IJsonSchema } from '@flowgram.ai/form-materials';

export interface AgentNodeJSON extends FlowNodeJSON {
  data: {
    title: string;
    outputs: IJsonSchema<'object'>;
    /**
     * Inline agent server connection config (no external registry).
     * `url` is the full /chat/process endpoint.
     */
    server: {
      url: string;
      /** Inferred schema, derived from headersValues by createInferInputsPlugin. */
      headers: IJsonSchema<'object'>;
      /** User-filled headers as flow values (constant / ref / template). */
      headersValues: Record<string, IFlowConstantRefValue>;
    };
    /** Agent template id (→ body.agent_id). */
    agentId: string;
    /** Caller identity (→ body.user_id). */
    userId: string;
    /** User message for this turn (→ body.input); may reference variables. */
    input: IFlowTemplateValue;
    /** Session/conversation id handling (→ body.session_id). */
    session: {
      auto: boolean;
      id: string;
    };
  };
}
