/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeJSON } from '@flowgram.ai/free-layout-editor';
import { IFlowValue, IJsonSchema } from '@flowgram.ai/form-materials';

export type CodeLanguage = 'javascript' | 'python';

export interface CodeScript {
  language: CodeLanguage;
  content: string;
}

export interface CodeNodeJSON extends FlowNodeJSON {
  data: {
    title: string;
    inputsValues: Record<string, IFlowValue>;
    inputs: IJsonSchema<'object'>;
    outputs: IJsonSchema<'object'>;
    script: CodeScript;
  };
}
