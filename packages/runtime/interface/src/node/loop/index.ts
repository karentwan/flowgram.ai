/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IFlowRefValue } from '@schema/value';
import { WorkflowNodeSchema } from '@schema/node';
import { FlowGramNode } from '@node/constant';
import { LoopMode } from './constant';

export { LoopMode };

interface LoopNodeData {
  title: string;
  loopFor: IFlowRefValue;
  loopOutputs: Record<string, IFlowRefValue>;
  /**
   * Execution mode (performance hint, not semantic — see LoopMode doc).
   * Defaults to Serial when absent (backward compatible).
   */
  mode?: LoopMode;
  /**
   * Max in-flight iterations when mode === Parallel. Ignored in Serial mode.
   * Actual concurrency = min(semaphore, loopFor.length). Soft cap at 20 — the
   * canvas warns above this value but allows override.
   * Must be a positive integer; canvas validates and blocks <= 0.
   */
  semaphore?: number;
}

export type LoopNodeSchema = WorkflowNodeSchema<FlowGramNode.Loop, LoopNodeData>;
