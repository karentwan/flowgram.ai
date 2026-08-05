/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { DisplayInputsValues, IFlowValue, InputsValues } from '@flowgram.ai/form-materials';
import { Input } from '@douyinfe/semi-ui';

import { useIsSidebar, useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

/**
 * Inline agent server connection config, editable on the canvas:
 *   - URL: the full /chat/process endpoint
 *   - Headers: flow values (constant / ref / template) — the same editor the
 *     HTTP node uses (InputsValues). Secrets are serialized with the workflow
 *     JSON (encrypted at rest by flow-backend), same trade-off as the HTTP node.
 *
 * The schema for the headers is inferred from `headersValues` by
 * createInferInputsPlugin (see form-meta.tsx), so the runtime executor gets a
 * typed declaration under `server.headers`.
 */
export function Server() {
  const { readonly } = useNodeRenderContext();
  const isSidebar = useIsSidebar();

  return (
    <>
      <FormItem name="URL" required vertical type="string">
        <Field<string> name="server.url" defaultValue="">
          {({ field }) => (
            <Input
              value={field.value}
              onChange={(value) => field.onChange(value)}
              disabled={readonly}
              placeholder="https://host/chat/process"
              size="small"
            />
          )}
        </Field>
      </FormItem>

      <FormItem name="Headers" vertical type="object">
        <Field<Record<string, IFlowValue | undefined> | undefined> name="server.headersValues">
          {({ field }) =>
            isSidebar ? (
              <InputsValues
                value={field.value}
                onChange={(value) => field.onChange(value)}
                readonly={readonly}
              />
            ) : (
              <DisplayInputsValues value={field.value} />
            )
          }
        </Field>
      </FormItem>
    </>
  );
}
