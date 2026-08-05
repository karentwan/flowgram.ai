/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { Input } from '@douyinfe/semi-ui';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

export function AgentId() {
  const { readonly } = useNodeRenderContext();
  return (
    <FormItem name="Agent ID" required vertical type="string">
      <Field<string> name="agentId" defaultValue="">
        {({ field }) => (
          <Input
            value={field.value}
            onChange={(value) => field.onChange(value)}
            disabled={readonly}
            placeholder="e.g. risk-agent"
            size="small"
          />
        )}
      </Field>
    </FormItem>
  );
}
