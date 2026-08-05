/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { DisplayInputsValues, IFlowValue, InputsValues } from '@flowgram.ai/form-materials';

import { useIsSidebar, useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

export function Args() {
  const { readonly } = useNodeRenderContext();
  const isSidebar = useIsSidebar();

  if (!isSidebar) {
    return (
      <FormItem name="args" type="object" vertical>
        <Field<Record<string, IFlowValue | undefined> | undefined> name="argsValues">
          {({ field }) => <DisplayInputsValues value={field.value} />}
        </Field>
      </FormItem>
    );
  }

  return (
    <FormItem name="args" type="object" vertical>
      <Field<Record<string, IFlowValue | undefined> | undefined> name="argsValues">
        {({ field }) => (
          <InputsValues
            value={field.value}
            onChange={(value) => field.onChange(value)}
            readonly={readonly}
          />
        )}
      </Field>
    </FormItem>
  );
}
