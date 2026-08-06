/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Studio top bar: workflow name, Save / Save as / Open / New, user + logout.
 *
 * Renders INSIDE the editor tree so it can read the live document via
 * `useService(WorkflowDocument)` for serialization on save. The bar is
 * absolutely positioned at the top of the editor container.
 */
import { useState, useEffect } from 'react';

import { useService, WorkflowDocument } from '@flowgram.ai/free-layout-editor';
import { Button, Input, Typography, Tag, Dropdown, Empty, Spin } from '@douyinfe/semi-ui';
import { IconSave, IconPlus, IconFolderOpen, IconChevronDown } from '@douyinfe/semi-icons';

import { api } from '../api/trpc';
import { useStudio } from './studio-context';

const DEFAULT_NAME = 'Untitled workflow';

export const StudioBar = () => {
  const document = useService(WorkflowDocument);
  const { current, user, logout, setCurrent, save, load, markDirty } = useStudio();

  const [name, setName] = useState(current?.name ?? DEFAULT_NAME);
  const [saving, setSaving] = useState(false);
  const [openList, setOpenList] = useState<{
    loading: boolean;
    items: Array<{ id: string; name: string; version: number; updatedAt: string }>;
  } | null>(null);
  const [error, setError] = useState('');

  // When a different workflow is loaded, sync the local name input.
  if (current?.name && current.name !== name && !current.dirty) {
    setName(current.name);
  }

  // Mark the workflow dirty whenever the document content changes (after load).
  useEffect(() => {
    const disposable = document.onContentChange(() => markDirty(true));
    return () => disposable.dispose();
  }, [document, markDirty]);

  const handleSave = async () => {
    setError('');
    setSaving(true);
    try {
      const docJson = document.toJSON();
      await save(name || DEFAULT_NAME, docJson as unknown as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAs = async () => {
    setError('');
    setSaving(true);
    try {
      // Force a create by clearing current, then save.
      setCurrent(null);
      const docJson = document.toJSON();
      await save(name || DEFAULT_NAME, docJson as unknown as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save as failed');
    } finally {
      setSaving(false);
    }
  };

  const handleNew = () => {
    if (current?.dirty && !window.confirm('Discard unsaved changes and start a new workflow?')) {
      return;
    }
    // Reload to a fresh editor (simplest: location reload clears state).
    window.location.href = window.location.pathname;
  };

  const openOpenList = async () => {
    setOpenList({ loading: true, items: [] });
    try {
      const items = await api.workflow.list();
      setOpenList({ loading: false, items });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to list workflows');
      setOpenList({ loading: false, items: [] });
    }
  };

  const handleOpen = async (id: string) => {
    // Confirm before discarding unsaved changes (same guard as New).
    if (current?.dirty && !window.confirm('Discard unsaved changes and open another workflow?')) {
      return;
    }
    setError('');
    try {
      const { document: docJson } = await load(id);
      // fromJSON merges into the existing canvas — clear first so the old
      // nodes/edges don't stack on top of the loaded workflow.
      document.clear();
      document.fromJSON(docJson as never);
      // clear/fromJSON both fire onContentChange → markDirty(true); reset so
      // a freshly loaded workflow shows as clean.
      markDirty(false);
      setOpenList(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to open workflow');
    }
  };

  return (
    <div
      style={{
        height: 48,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 16px',
        background: '#fff',
        borderBottom: '1px solid #e8e8e8',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}
    >
      <Typography.Title heading={5} style={{ margin: 0, marginRight: 8, whiteSpace: 'nowrap' }}>
        Flowgram Studio
      </Typography.Title>

      <Input
        value={name}
        onChange={(v) => setName(v)}
        placeholder={DEFAULT_NAME}
        size="small"
        style={{ width: 220 }}
      />

      {current && (
        <Tag size="small" color={current.dirty ? 'orange' : 'green'}>
          {current.dirty ? 'Unsaved' : `v${current.version}`}
        </Tag>
      )}

      <Button
        icon={<IconSave />}
        theme="solid"
        type="primary"
        size="small"
        loading={saving}
        onClick={handleSave}
      >
        Save
      </Button>
      <Button icon={<IconPlus />} size="small" onClick={handleSaveAs}>
        Save as
      </Button>

      <Dropdown
        trigger="click"
        position="bottomRight"
        onVisibleChange={(v) => v && openOpenList()}
        render={
          <Dropdown.Menu style={{ width: 300, maxHeight: 400, overflow: 'auto' }}>
            {openList?.loading && (
              <div style={{ padding: 24, textAlign: 'center' }}>
                <Spin />
              </div>
            )}
            {!openList?.loading && openList?.items.length === 0 && (
              <Empty description="No saved workflows" />
            )}
            {openList?.items.map((wf) => (
              <Dropdown.Item key={wf.id} onClick={() => handleOpen(wf.id)}>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span>{wf.name}</span>
                  <Typography.Text type="tertiary" style={{ fontSize: 12 }}>
                    v{wf.version}
                  </Typography.Text>
                </div>
              </Dropdown.Item>
            ))}
          </Dropdown.Menu>
        }
      >
        <Button icon={<IconFolderOpen />} size="small">
          Open <IconChevronDown size="small" />
        </Button>
      </Dropdown>

      <Button size="small" onClick={handleNew}>
        New
      </Button>

      {error && (
        <Typography.Text type="danger" style={{ fontSize: 12 }}>
          {error}
        </Typography.Text>
      )}

      <div style={{ flex: 1 }} />

      <Typography.Text type="tertiary" style={{ fontSize: 13 }}>
        {user?.name}
      </Typography.Text>
      <Button size="small" type="tertiary" onClick={logout}>
        Sign out
      </Button>
    </div>
  );
};
