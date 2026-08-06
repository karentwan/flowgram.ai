/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { DockedPanelLayer } from '@flowgram.ai/panel-manager-plugin';
import { EditorRenderer, FreeLayoutEditorProvider } from '@flowgram.ai/free-layout-editor';

import '@flowgram.ai/free-layout-editor/index.css';
import './styles/index.css';
import { StudioProvider, useStudio } from './studio/studio-context';
import { StudioBar } from './studio/studio-bar';
import { AuthGate } from './studio/auth-gate';
import { nodeRegistries } from './nodes';
import { initialData } from './initial-data';
import { useEditorProps } from './hooks';

const EditorInner = () => {
  const editorProps = useEditorProps(initialData, nodeRegistries);
  return (
    <div
      className="doc-free-feature-overview"
      style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}
    >
      <FreeLayoutEditorProvider {...editorProps}>
        <StudioBar />
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <div className="demo-container">
            <DockedPanelLayer>
              <EditorRenderer className="demo-editor" />
            </DockedPanelLayer>
          </div>
        </div>
      </FreeLayoutEditorProvider>
    </div>
  );
};

export const Editor = () => {
  const { authReady, user } = useStudio();
  if (!authReady) return null; // resolving stored session
  if (!user) return <AuthGate />;
  return <EditorInner />;
};

export const StudioApp = () => (
  <StudioProvider>
    <Editor />
  </StudioProvider>
);
