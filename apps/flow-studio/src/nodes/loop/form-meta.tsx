/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { LoopMode } from '@flowgram.ai/runtime-interface';
import { FormRenderProps, FlowNodeJSON, Field, FormMeta } from '@flowgram.ai/free-layout-editor';
import { SubCanvasRender } from '@flowgram.ai/free-container-plugin';
import {
  BatchOutputs,
  BatchVariableSelector,
  createBatchOutputsFormPlugin,
  DisplayOutputs,
  IFlowRefValue,
  provideBatchInputEffect,
} from '@flowgram.ai/form-materials';
import { Select, InputNumber } from '@douyinfe/semi-ui';

import { defaultFormMeta } from '../default-form-meta';
import { useIsSidebar, useNodeRenderContext } from '../../hooks';
import { FormHeader, FormContent, FormItem, Feedback } from '../../form-components';

interface LoopNodeJSON extends FlowNodeJSON {
  data: {
    loopFor: IFlowRefValue;
    mode?: LoopMode;
    semaphore?: number;
  };
}

export const LoopFormRender = ({ form }: FormRenderProps<LoopNodeJSON>) => {
  const isSidebar = useIsSidebar();
  const { readonly } = useNodeRenderContext();
  const formHeight = 115;

  const loopFor = (
    <Field<IFlowRefValue> name={`loopFor`}>
      {({ field, fieldState }) => (
        <FormItem name={'loopFor'} type={'array'} required>
          <BatchVariableSelector
            style={{ width: '100%' }}
            value={field.value?.content}
            onChange={(val) => field.onChange({ type: 'ref', content: val })}
            readonly={readonly}
            hasError={Object.keys(fieldState?.errors || {}).length > 0}
          />
          <Feedback errors={fieldState?.errors} />
        </FormItem>
      )}
    </Field>
  );

  const loopOutputs = (
    <Field<Record<string, IFlowRefValue | undefined> | undefined> name={`loopOutputs`}>
      {({ field, fieldState }) => (
        <FormItem name="loopOutputs" type="object" vertical>
          <BatchOutputs
            style={{ width: '100%' }}
            value={field.value}
            onChange={(val) => field.onChange(val)}
            readonly={readonly}
            hasError={Object.keys(fieldState?.errors || {}).length > 0}
          />
          <Feedback errors={fieldState?.errors} />
        </FormItem>
      )}
    </Field>
  );

  // Execution mode + concurrency. Performance hints only (see LoopMode doc /
  // IR contract §5) — they don't affect output order, error propagation, or
  // break semantics. Semaphore is only meaningful in Parallel mode.
  const concurrency = (
    <div style={{ display: 'flex', gap: 5 }}>
      <FormItem name="Mode" type="string" style={{ flex: 1 }}>
        <Field<LoopMode> name="mode" defaultValue={LoopMode.Serial}>
          {({ field }) => (
            <Select
              value={field.value ?? LoopMode.Serial}
              onChange={(value) => field.onChange(value as LoopMode)}
              style={{ width: '100%' }}
              size="small"
              disabled={readonly}
              optionList={[
                { label: 'Serial', value: LoopMode.Serial },
                { label: 'Parallel', value: LoopMode.Parallel },
              ]}
            />
          )}
        </Field>
      </FormItem>
      <Field<number | undefined> name="semaphore">
        {({ field }) => (
          <FormItem
            name="Concurrency"
            type="number"
            style={{ flex: 1, visibility: field.value === undefined ? 'hidden' : undefined }}
          >
            <InputNumber
              value={field.value}
              onChange={(value) => field.onChange(value as number | undefined)}
              placeholder="∞"
              size="small"
              disabled={readonly}
              min={1}
              max={20}
              style={{ width: '100%' }}
            />
          </FormItem>
        )}
      </Field>
    </div>
  );

  if (isSidebar) {
    return (
      <>
        <FormHeader />
        <FormContent>
          {loopFor}
          {loopOutputs}
          {concurrency}
        </FormContent>
      </>
    );
  }
  return (
    <>
      <FormHeader />
      <FormContent>
        {loopFor}
        {concurrency}
        <SubCanvasRender offsetY={-formHeight} />
        <DisplayOutputs displayFromScope />
      </FormContent>
    </>
  );
};

export const formMeta: FormMeta = {
  ...defaultFormMeta,
  render: LoopFormRender,
  effect: {
    loopFor: provideBatchInputEffect,
  },
  validate: {
    // semaphore must be a positive integer when set; <= 0 is invalid (hard block).
    // Values > 20 are allowed (soft cap) but warned — see IR contract §5.
    semaphore: ({ value }) => {
      if (value === undefined || value === null) {
        return undefined;
      }
      if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
        return 'Concurrency must be a positive integer';
      }
      return undefined;
    },
  },
  plugins: [createBatchOutputsFormPlugin({ outputKey: 'loopOutputs', inferTargetKey: 'outputs' })],
};
