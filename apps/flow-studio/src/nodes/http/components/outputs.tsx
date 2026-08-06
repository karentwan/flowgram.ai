/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { DisplayOutputs, IJsonSchema, JsonSchemaEditor } from '@flowgram.ai/form-materials';
import { Divider } from '@douyinfe/semi-ui';

import { useIsSidebar, useNodeRenderContext } from '../../../hooks';
import { FormItem } from '../../../form-components';

/**
 * Editable outputs schema for the HTTP node. The default outputs
 * ({ body, headers, statusCode }) plus the flattened JSON body fields let
 * users declare the response shape so downstream nodes (Loop, Agent) can
 * pick fields from the variable tree — same JsonSchemaEditor as Code/MCP.
 */
export function Outputs() {
  const { readonly } = useNodeRenderContext();
  const isSidebar = useIsSidebar();

  if (!isSidebar) {
    return (
      <>
        <Divider />
        <Field<IJsonSchema> name="outputs">
          {({ field }) => <DisplayOutputs value={field.value} />}
        </Field>
      </>
    );
  }

  return (
    <>
      <Divider />
      <FormItem name="outputs" type="object" vertical>
        <Field<IJsonSchema> name="outputs">
          {({ field }) => (
            <JsonSchemaEditor
              readonly={readonly}
              value={field.value}
              onChange={(value) => field.onChange(value)}
            />
          )}
        </Field>
      </FormItem>
    </>
  );
}
