/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { nanoid } from 'nanoid';

import { WorkflowNodeType } from '../constants';
import { FlowNodeRegistry } from '../../typings';
import iconAgent from '../../assets/icon-agent.svg';
import { formMeta } from './form-meta';

let index = 0;

export const AgentNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Agent,
  info: {
    icon: iconAgent,
    description: 'Call an agent (chat endpoint)',
  },
  meta: {
    size: {
      width: 360,
      height: 460,
    },
  },
  onAdd() {
    return {
      id: `agent_${nanoid(5)}`,
      type: 'agent',
      data: {
        title: `Agent_${++index}`,
        server: {
          url: '',
          headers: { type: 'object' },
          headersValues: {},
        },
        agentId: '',
        userId: 'anonymous',
        input: {
          type: 'template',
          content: '',
        },
        session: {
          auto: true,
          id: '',
        },
        timeout: {
          timeout: 120000,
        },
        // reply: concatenated assistant text; usage: token counts from the run.
        outputs: {
          type: 'object',
          properties: {
            reply: { type: 'string' },
            usage: { type: 'object' },
          },
        },
      },
    };
  },
  formMeta: formMeta,
};
