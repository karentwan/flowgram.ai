/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Loop execution mode (grill decision: stance A — semantics follow LangGraph).
 *
 * `mode` and `semaphore` are PERFORMANCE HINTS only — they do NOT affect output
 * order, error propagation, or break semantics (all follow LangGraph). They only
 * tell the Python executor how to schedule loop iterations.
 *
 * See packages/runtime/interface/src/langgraph-ir/contract.md §5.
 */
export enum LoopMode {
  /** Iterate sequentially (default; backward compatible with existing loops). */
  Serial = 'serial',
  /** Fan-out via LangGraph Send; semaphore optionally caps in-flight workers. */
  Parallel = 'parallel',
}
