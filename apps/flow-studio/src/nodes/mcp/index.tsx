/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { nanoid } from 'nanoid';

import { WorkflowNodeType } from '../constants';
import { FlowNodeRegistry } from '../../typings';
import iconMCP from '../../assets/icon-mcp.svg';
import { formMeta } from './form-meta';

let index = 0;

export const MCPNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.MCP,
  info: {
    icon: iconMCP,
    description: 'Call an MCP tool',
  },
  meta: {
    size: {
      width: 360,
      height: 420,
    },
  },
  onAdd() {
    return {
      id: `mcp_${nanoid(5)}`,
      type: 'mcp',
      data: {
        title: `MCP_${++index}`,
        server: {
          url: '',
          headers: { type: 'object' },
          headersValues: {},
        },
        toolName: '',
        args: {},
        argsValues: {},
        timeout: {
          retryTimes: 1,
          timeout: 30000,
        },
        // Default to the MCP CallToolResult envelope; structuredContent is the
        // tool-specific payload users refine per node.
        outputs: {
          type: 'object',
          properties: {
            content: { type: 'array', items: { type: 'object' } },
            isError: { type: 'boolean' },
            structuredContent: { type: 'object' },
          },
        },
      },
    };
  },
  formMeta: formMeta,
};
