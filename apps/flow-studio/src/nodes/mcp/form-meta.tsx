/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormMeta, FormRenderProps } from '@flowgram.ai/free-layout-editor';
import { createInferInputsPlugin, DisplayOutputs } from '@flowgram.ai/form-materials';
import { Divider } from '@douyinfe/semi-ui';

import { FormHeader, FormContent } from '../../form-components';
import { MCPNodeJSON } from './types';
import { ToolSelect } from './components/tool-select';
import { Timeout } from './components/timeout';
import { Server } from './components/server';
import { Args } from './components/args';
import { defaultFormMeta } from '../default-form-meta';

export const FormRender = ({ form }: FormRenderProps<MCPNodeJSON>) => (
  <>
    <FormHeader />
    <FormContent>
      <Server />
      <Divider />
      <ToolSelect />
      <Divider />
      <Args />
      <Divider />
      <Timeout />
      <Divider />
      <DisplayOutputs displayFromScope />
    </FormContent>
  </>
);

export const formMeta: FormMeta = {
  render: (props) => <FormRender {...props} />,
  effect: defaultFormMeta.effect,
  plugins: [
    // Derive the tool-arguments input schema from the user-filled argsValues,
    // so the runtime executor receives a typed `args` JsonSchema declaration.
    createInferInputsPlugin({ sourceKey: 'argsValues', targetKey: 'args' }),
    // Derive the request-headers schema from headersValues (nested under
    // `server`). lodash get/set underpins the plugin, so nested paths work.
    createInferInputsPlugin({ sourceKey: 'server.headersValues', targetKey: 'server.headers' }),
  ],
};
