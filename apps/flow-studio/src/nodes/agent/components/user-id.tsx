/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { Input } from '@douyinfe/semi-ui';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

export function UserId() {
  const { readonly } = useNodeRenderContext();
  return (
    <FormItem name="User ID" required vertical type="string">
      <Field<string> name="userId" defaultValue="anonymous">
        {({ field }) => (
          <Input
            value={field.value}
            onChange={(value) => field.onChange(value)}
            disabled={readonly}
            placeholder="anonymous"
            size="small"
          />
        )}
      </Field>
    </FormItem>
  );
}
