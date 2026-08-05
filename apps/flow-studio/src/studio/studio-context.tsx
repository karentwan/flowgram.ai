/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Studio state: tracks the currently-open workflow (id / version / name /
 * dirty flag) and the authenticated user. The StudioBar reads this; the editor
 * reads `document` for initial load and writes via `markDirty()`.
 *
 * Persisted-workflow actions (save / load / new) talk to flow-backend through
 * the tRPC client in `src/api/trpc.ts`.
 */
import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

import { api, getApiKey, setApiKey, clearApiKey } from '../api/trpc';

export interface StudioUser {
  id: string;
  name: string;
}

export interface WorkflowRef {
  id: string;
  name: string;
  version: number;
}

interface StudioState {
  user: StudioUser | null;
  authReady: boolean;
  // The currently open workflow (null = unsaved "new" doc, no server id yet).
  current: (WorkflowRef & { dirty: boolean }) | null;
}

interface StudioContextValue extends StudioState {
  /** Verify a stored API key and resolve the user; returns the user or null. */
  login: (apiKey: string) => Promise<StudioUser | null>;
  logout: () => void;
  /** Called by the editor whenever the document is first loaded or mutates. */
  setCurrent: (wf: WorkflowRef | null) => void;
  markDirty: (dirty: boolean) => void;
  /** Save the given document to the backend (create or update). */
  save: (name: string, document: Record<string, unknown>) => Promise<void>;
  /** Load a workflow document from the backend (returns the JSON). */
  load: (
    id: string
  ) => Promise<{ document: Record<string, unknown>; name: string; version: number }>;
}

const StudioContext = createContext<StudioContextValue | null>(null);

export const useStudio = (): StudioContextValue => {
  const ctx = useContext(StudioContext);
  if (!ctx) throw new Error('useStudio must be used within StudioProvider');
  return ctx;
};

export const StudioProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<StudioState>({ user: null, authReady: false, current: null });

  // On mount, if an API key is stored, verify it and resolve the user.
  useEffect(() => {
    const key = getApiKey();
    if (!key) {
      setState((s) => ({ ...s, authReady: true }));
      return;
    }
    api.auth
      .whoami()
      .then((user) => setState((s) => ({ ...s, user, authReady: true })))
      .catch(() => {
        clearApiKey();
        setState((s) => ({ ...s, user: null, authReady: true }));
      });
  }, []);

  const login = useCallback(async (apiKey: string): Promise<StudioUser | null> => {
    setApiKey(apiKey);
    const user = await api.auth.whoami();
    if (!user) {
      clearApiKey();
      return null;
    }
    setState((s) => ({ ...s, user }));
    return user;
  }, []);

  const logout = useCallback(() => {
    clearApiKey();
    setState((s) => ({ ...s, user: null, current: null }));
  }, []);

  const setCurrent = useCallback((wf: WorkflowRef | null) => {
    setState((s) => ({ ...s, current: wf ? { ...wf, dirty: false } : null }));
  }, []);

  const markDirty = useCallback((dirty: boolean) => {
    setState((s) => (s.current ? { ...s, current: { ...s.current, dirty } } : s));
  }, []);

  const save = useCallback(
    async (name: string, document: Record<string, unknown>) => {
      const { current } = state;
      if (current) {
        // Update existing workflow (optimistic version bump handled server-side).
        const updated = await api.workflow.update({
          id: current.id,
          name,
          document,
          version: current.version,
        });
        setState((s) => ({
          ...s,
          current: { id: updated.id, name, version: updated.version, dirty: false },
        }));
      } else {
        // First save: create a new workflow.
        const created = await api.workflow.create({ name, document });
        setState((s) => ({
          ...s,
          current: { id: created.id, name, version: created.version, dirty: false },
        }));
      }
    },
    [state.current]
  );

  const load = useCallback(async (id: string) => {
    const wf = await api.workflow.get(id);
    setState((s) => ({
      ...s,
      current: { id: wf.id, name: wf.name, version: wf.version, dirty: false },
    }));
    return { document: wf.document, name: wf.name, version: wf.version };
  }, []);

  const value: StudioContextValue = {
    ...state,
    login,
    logout,
    setCurrent,
    markDirty,
    save,
    load,
  };

  return <StudioContext.Provider value={value}>{children}</StudioContext.Provider>;
};
