/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * LangGraph IR constants.
 *
 * These mirror the Python backend's node executor modules (see
 * `apps/flow-backend-python/app/nodes/`). Keeping the mapping in one place on
 * the TS side lets the canvas emit self-describing IR and lets tooling validate
 * node types against the Python surface.
 *
 * See `./contract.md` for the full interpretation contract.
 */

/**
 * Separator used to build flat LangGraph State field names from a node id +
 * output field name. Double underscore to avoid clashing with single-underscore
 * identifiers in node ids / field names.
 *
 * Example: node `llm_0` output `result` → State field `llm_0__result`.
 *
 * This is a HARD invariant: the Python loader uses the same separator.
 */
export const STATE_FIELD_SEPARATOR = '__';

/**
 * Suffix used for loop-local variable scopes. A loop node with id `loop_0`
 * exposes its iteration variables under the synthetic scope id `loop_0_locals`.
 * Variable refs in the canvas use `['loop_0_locals', 'item'|'index']`.
 */
export const LOOP_LOCALS_SUFFIX = '_locals';

/**
 * Marker prefix for AES-256-GCM encrypted secret values (mirrors Node backend
 * `lib/crypto.ts`). Both backends must produce/consume the same format so
 * secrets encrypted on one side decrypt on the other.
 */
export const ENCRYPTED_VALUE_PREFIX = 'enc::';

/**
 * Canvas-visible node types that the Python executor recognizes.
 *
 * This is the authoritative list of `node.type` values the LangGraph loader
 * will dispatch on. Values not in this map are rejected by the loader.
 *
 * The value is the Python module name (under `app/nodes/`) implementing the
 * node. `null` means the type is structurally present in the canvas schema but
 * ignored by the executor (block-start/block-end are subgraph markers; the
 * loader infers subgraph entry/exit from edges).
 */
export const NODE_TYPE_TO_PYTHON_MODULE: Readonly<Record<string, string | null>> = Object.freeze({
  start: 'start',
  end: 'end',
  llm: 'llm',
  http: 'http',
  code: 'code',
  condition: 'condition',
  loop: 'loop',
  break: 'break',
  mcp: 'mcp',
  agent: 'agent',
  // Subgraph boundary markers — present in canvas JSON, ignored by executor.
  'block-start': null,
  'block-end': null,
  // Visual-only node types — ignored by executor.
  comment: null,
  group: null,
  root: null,
});

/**
 * Node types explicitly REMOVED by the grill decision. If the loader encounters
 * any of these in IR, it rejects the workflow (rather than silently ignoring),
 * so users learn the feature is gone.
 */
export const REMOVED_NODE_TYPES: ReadonlySet<string> = Object.freeze(new Set(['continue']));
