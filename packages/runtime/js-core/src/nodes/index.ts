/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { INodeExecutorFactory } from '@flowgram.ai/runtime-interface';

import { StartExecutor } from './start';
import { MCPExecutor } from './mcp';
import { LoopExecutor } from './loop';
import { LLMExecutor } from './llm';
import { HTTPExecutor } from './http';
import { EndExecutor } from './end';
import { BlockEndExecutor, BlockStartExecutor } from './empty';
import { ContinueExecutor } from './continue';
import { ConditionExecutor } from './condition';
import { CodeExecutor } from './code';
import { BreakExecutor } from './break';
import { AgentExecutor } from './agent';

export const WorkflowRuntimeNodeExecutors: INodeExecutorFactory[] = [
  StartExecutor,
  EndExecutor,
  LLMExecutor,
  ConditionExecutor,
  LoopExecutor,
  BlockStartExecutor,
  BlockEndExecutor,
  HTTPExecutor,
  MCPExecutor,
  AgentExecutor,
  CodeExecutor,
  BreakExecutor,
  ContinueExecutor,
];
