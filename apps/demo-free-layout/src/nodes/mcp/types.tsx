/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IFlowConstantRefValue } from '@flowgram.ai/runtime-interface';
import { FlowNodeJSON } from '@flowgram.ai/free-layout-editor';
import { IJsonSchema } from '@flowgram.ai/form-materials';

export interface MCPNodeJSON extends FlowNodeJSON {
  data: {
    title: string;
    outputs: IJsonSchema<'object'>;
    /**
     * Inline server connection config (no external registry).
     */
    server: {
      url: string;
      /** Inferred schema, derived from headersValues by createInferInputsPlugin. */
      headers: IJsonSchema<'object'>;
      /** User-filled headers as flow values (constant / ref / template). */
      headersValues: Record<string, IFlowConstantRefValue>;
    };
    /**
     * The MCP tool to call (chosen via tools/list discovery).
     */
    toolName: string;
    /**
     * Inferred input schema for the tool arguments.
     */
    args: IJsonSchema<'object'>;
    /**
     * User-filled tool arguments as flow values.
     */
    argsValues: Record<string, IFlowConstantRefValue>;
    timeout: {
      retryTimes: number;
      timeout: number;
    };
  };
}
