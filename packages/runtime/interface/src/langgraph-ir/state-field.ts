/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { STATE_FIELD_SEPARATOR, LOOP_LOCALS_SUFFIX } from './constant';

/**
 * Build a flat LangGraph State field name from a node id + output field name.
 *
 * Invariant (contract.md §3): `{nodeId}__{fieldName}`.
 *
 * The Python loader mirrors this exact rule when constructing its Pydantic State
 * model, so the two sides stay in sync by construction.
 *
 * @example buildStateField('llm_0', 'result') === 'llm_0__result'
 */
export function buildStateField(nodeId: string, fieldName: string): string {
  return `${nodeId}${STATE_FIELD_SEPARATOR}${fieldName}`;
}

/**
 * True if `s` looks like a loop-locals scope id (e.g. `loop_0_locals`).
 * Such ids are synthetic and only valid inside a loop subgraph's variable refs.
 */
export function isLoopLocalsScope(s: string): boolean {
  return s.endsWith(LOOP_LOCALS_SUFFIX);
}

/**
 * Resolve an `IFlowRefValue.content` path to a State field name (for the
 * leading two segments) plus an optional nested-key tail.
 *
 * Contract.md §3:
 *   ['llm_0','result']              → { field: 'llm_0__result' }
 *   ['http_0','body','name']        → { field: 'http_0__body', nested: ['name'] }
 *   ['loop_0_locals','item']        → { loopLocals: 'item' }   (subgraph-local)
 *   ['loop_0_locals','index']       → { loopLocals: 'index' }
 *
 * Returns `null` for paths that don't match any recognized shape so callers
 * can reject them explicitly (the loader never silently drops a ref).
 */
export function resolveRefPath(
  path: string[]
): { field: string; nested?: string[] } | { loopLocals: 'item' | 'index' | string } | null {
  if (!Array.isArray(path) || path.length === 0) return null;

  const [head, second, ...rest] = path;

  // Loop-locals scope: ['loop_0_locals', 'item' | 'index' | ...]
  if (typeof head === 'string' && isLoopLocalsScope(head)) {
    return { loopLocals: second ?? '' };
  }

  // Standard node ref: ['nodeId', 'field', ...nested?]
  if (typeof head === 'string' && typeof second === 'string') {
    const field = buildStateField(head, second);
    return rest.length > 0 ? { field, nested: rest } : { field };
  }

  return null;
}
