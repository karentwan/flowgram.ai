/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormMeta, FormRenderProps } from '@flowgram.ai/free-layout-editor';
import { createInferInputsPlugin, DisplayOutputs } from '@flowgram.ai/form-materials';
import { Divider } from '@douyinfe/semi-ui';

import { FormHeader, FormContent } from '../../form-components';
import { AgentNodeJSON } from './types';
import { UserId } from './components/user-id';
import { Timeout } from './components/timeout';
import { Session } from './components/session';
import { Server } from './components/server';
import { Input } from './components/input';
import { AgentId } from './components/agent-id';
import { defaultFormMeta } from '../default-form-meta';

export const FormRender = ({ form }: FormRenderProps<AgentNodeJSON>) => (
  <>
    <FormHeader />
    <FormContent>
      <Server />
      <Divider />
      <AgentId />
      <Divider />
      <UserId />
      <Divider />
      <Input />
      <Divider />
      <Session />
      <Divider />
      <Timeout />
      <Divider />
      <DisplayOutputs displayFromScope />
    </FormContent>
  </>
);

export const formMeta: FormMeta = {
  render: (props) => <FormRender {...props} />,
  // Reuse the default effects so `outputs` is published as variables
  // (provideJsonSchemaOutputs) and the title stays in sync.
  effect: defaultFormMeta.effect,
  plugins: [
    // Derive the request-headers schema from headersValues (nested under
    // `server`). lodash get/set underpins the plugin, so nested paths work.
    createInferInputsPlugin({ sourceKey: 'server.headersValues', targetKey: 'server.headers' }),
  ],
};
