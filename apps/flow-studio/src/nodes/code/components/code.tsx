/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor';
import { PythonCodeEditor, TypeScriptCodeEditor } from '@flowgram.ai/form-materials';
import { Select } from '@douyinfe/semi-ui';

import { CodeLanguage, CodeScript } from '../types';
import { DEFAULT_JS_CODE, DEFAULT_PYTHON_CODE } from '../constants';
import { useIsSidebar, useNodeRenderContext } from '../../../hooks';

export function Code() {
  const isSidebar = useIsSidebar();
  const { readonly } = useNodeRenderContext();

  if (!isSidebar) {
    return null;
  }

  return (
    <Field<CodeScript> name="script">
      {({ field }) => {
        const { language = 'javascript', content } = field.value || {};
        const switchLanguage = (next: CodeLanguage) => {
          if (next === language) {
            return;
          }
          // Replace the content only when it is untouched (empty or a template).
          const isTemplate =
            !content?.trim() || content === DEFAULT_JS_CODE || content === DEFAULT_PYTHON_CODE;
          field.onChange({
            language: next,
            content: isTemplate
              ? next === 'python'
                ? DEFAULT_PYTHON_CODE
                : DEFAULT_JS_CODE
              : content,
          });
        };

        return (
          <>
            <Select
              value={language}
              onChange={(value) => switchLanguage(value as CodeLanguage)}
              disabled={readonly}
              style={{ width: '100%', marginBottom: 8 }}
              optionList={[
                { value: 'javascript', label: 'JavaScript' },
                { value: 'python', label: 'Python' },
              ]}
            />
            {language === 'python' ? (
              <PythonCodeEditor
                value={content}
                onChange={(value) => field.onChange({ language, content: value })}
                readonly={readonly}
              />
            ) : (
              <TypeScriptCodeEditor
                value={content}
                onChange={(value) => field.onChange({ language, content: value })}
                readonly={readonly}
              />
            )}
          </>
        );
      }}
    </Field>
  );
}
