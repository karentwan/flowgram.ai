/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * LangGraph IR contract.
 *
 * Defines how a FlowGram `WorkflowSchema` (the canvas product) is interpreted
 * by the Python LangGraph backend. See `./contract.md` for the full contract.
 *
 * This module is consumed by:
 *   - the canvas (apps/flow-studio) to emit/validate IR
 *   - tooling/tests to assert IR shape
 *   - the Python loader mirrors these rules in Pydantic (app/schemas/ir.py)
 */
export {
  STATE_FIELD_SEPARATOR,
  LOOP_LOCALS_SUFFIX,
  ENCRYPTED_VALUE_PREFIX,
  NODE_TYPE_TO_PYTHON_MODULE,
  REMOVED_NODE_TYPES,
} from './constant';
export { buildStateField, isLoopLocalsScope, resolveRefPath } from './state-field';
