/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { nanoid } from 'nanoid';

import { WorkflowNodeType } from '../constants';
import { FlowNodeRegistry } from '../../typings';
import iconCode from '../../assets/icon-script.png';
import { formMeta } from './form-meta';
import { DEFAULT_PYTHON_CODE } from './constants';

let index = 0;

export const CodeNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Code,
  info: {
    icon: iconCode,
    description: 'Run the Script',
  },
  meta: {
    size: {
      width: 360,
      height: 390,
    },
  },
  onAdd() {
    return {
      id: `code_${nanoid(5)}`,
      type: 'code',
      data: {
        title: `Code_${++index}`,
        inputsValues: {
          input: { type: 'constant', content: '' },
        },
        script: {
          language: 'python',
          content: DEFAULT_PYTHON_CODE,
        },
        outputs: {
          type: 'object',
          properties: {
            key0: {
              type: 'string',
            },
            key1: {
              type: 'array',
              items: {
                type: 'string',
              },
            },
            key2: {
              type: 'object',
              properties: {
                key21: {
                  type: 'string',
                },
              },
            },
          },
        },
      },
    };
  },
  formMeta: formMeta,
};
