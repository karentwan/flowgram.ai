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
 * Editable outputs schema for the MCP node. The default outputs
 * ({ content, isError, structuredContent }) only declare structuredContent as
 * a bare `object`, so downstream nodes (e.g. Loop's loopFor) cannot pick a
 * nested array like `structuredContent.数据列表` from the variable tree.
 *
 * Letting the user refine the outputs schema (same JsonSchemaEditor the Code
 * node uses) makes nested fields visible to the variable selector and gives
 * Loop the array itemsType it needs to iterate.
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
