/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { InputNumber } from '@douyinfe/semi-ui';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

/**
 * Per-call timeout (ms) for the agent /chat/process request. Default 120000
 * (2 min); raise it for slow agents (long LLM runs).
 */
export function Timeout() {
  const { readonly } = useNodeRenderContext();

  return (
    <FormItem name="Timeout(ms)" required type="number">
      <Field<number> name="timeout.timeout" defaultValue={120000}>
        {({ field }) => (
          <InputNumber
            size="small"
            value={field.value}
            onChange={(value) => field.onChange(value as number)}
            disabled={readonly}
            style={{ width: '100%' }}
            min={0}
          />
        )}
      </Field>
    </FormItem>
  );
}
