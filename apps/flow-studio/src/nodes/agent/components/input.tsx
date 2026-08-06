/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { IFlowTemplateValue, PromptEditorWithVariables } from '@flowgram.ai/form-materials';

import { useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

/**
 * The user message for this turn (→ body.input). Conversation history lives
 * server-side keyed by sessionId, so only the new message is composed here.
 * The prompt editor supports inline variable references via `{`.
 */
export function Input() {
  const { readonly } = useNodeRenderContext();
  return (
    <FormItem name="Input" required vertical>
      <Field<IFlowTemplateValue> name="input" defaultValue={{ type: 'template', content: '' }}>
        {({ field }) => (
          <PromptEditorWithVariables
            readonly={readonly}
            style={{ flexGrow: 1 }}
            placeholder="Type a message, use var by '{'"
            value={field.value}
            onChange={(value) => field.onChange(value!)}
          />
        )}
      </Field>
    </FormItem>
  );
}
