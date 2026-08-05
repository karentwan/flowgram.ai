/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Auth gate: shown when there's no valid API key. The user pastes their
 * flow-backend API key (printed by `pnpm seed` / init.sql); we verify it via
 * `auth.whoami` and store it in localStorage on success.
 */
import { useState } from 'react';

import { Input, Button, Typography } from '@douyinfe/semi-ui';

import { useStudio } from './studio-context';

export const AuthGate = () => {
  const { login } = useStudio();
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError('');
    setLoading(true);
    try {
      const user = await login(key.trim());
      if (!user) setError('Invalid API key. Check the key and try again.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f7fa',
      }}
    >
      <div
        style={{
          width: 380,
          padding: 32,
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        }}
      >
        <Typography.Title heading={3} style={{ marginBottom: 8 }}>
          Flowgram Studio
        </Typography.Title>
        <Typography.Text type="tertiary" style={{ display: 'block', marginBottom: 24 }}>
          Paste your API key to sign in. Get one from <code>pnpm seed</code> or the init SQL.
        </Typography.Text>
        <Input
          value={key}
          onChange={(v) => setKey(v)}
          placeholder="fk_..."
          size="large"
          onEnterPress={submit}
          disabled={loading}
        />
        {error && (
          <Typography.Text type="danger" style={{ display: 'block', marginTop: 8, fontSize: 13 }}>
            {error}
          </Typography.Text>
        )}
        <Button
          theme="solid"
          type="primary"
          size="large"
          block
          style={{ marginTop: 16 }}
          loading={loading}
          disabled={!key.trim()}
          onClick={submit}
        >
          Sign in
        </Button>
      </div>
    </div>
  );
};
