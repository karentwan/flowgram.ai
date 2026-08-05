/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { Input, Checkbox } from '@douyinfe/semi-ui';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

/**
 * Session/conversation id handling (→ body.session_id):
 *   - "Auto-generate" checked → a fresh id is created per workflow run
 *     (each run starts a new conversation).
 *   - unchecked → use the fixed id verbatim to continue an existing
 *     conversation across runs.
 */
export function Session() {
  const { readonly } = useNodeRenderContext();
  return (
    <FormItem name="Session" vertical>
      <Field<boolean> name="session.auto" defaultValue>
        {({ field: autoField }) => (
          <Field<string> name="session.id" defaultValue="">
            {({ field: idField }) => (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <Checkbox
                  checked={autoField.value}
                  onChange={(checked) => autoField.onChange(Boolean(checked))}
                  disabled={readonly}
                >
                  Auto-generate (new conversation per run)
                </Checkbox>
                <Input
                  value={idField.value}
                  onChange={(value) => idField.onChange(value)}
                  disabled={readonly || autoField.value}
                  placeholder="existing session id"
                  size="small"
                />
              </div>
            )}
          </Field>
        )}
      </Field>
    </FormItem>
  );
}
