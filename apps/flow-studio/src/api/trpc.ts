/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * tRPC client for flow-studio → flow-backend.
 *
 * Uses the raw tRPC HTTP request format (no superjson transformer — the backend
 * uses plain JSON). The Bearer API key is read from localStorage and attached
 * to every request as the Authorization header.
 *
 * NOTE: we hand-roll a thin fetch wrapper rather than `createTRPCClient` so the
 * bundle stays small and we avoid importing the backend's AppRouter type (which
 * would pull Prisma etc. into the browser bundle). The procedure paths match
 * the backend router exactly: `auth.whoami`, `workflow.list`, etc.
 */

const BACKEND_URL =
  (typeof window !== 'undefined' && window.__FLOW_BACKEND_URL__) || 'http://localhost:4100';
export const setBackendUrl = (url: string): void => {
  if (typeof window !== 'undefined') window.__FLOW_BACKEND_URL__ = url;
};

const API_KEY_STORAGE = 'flowgram.apiKey';
export const getApiKey = (): string | null => {
  try {
    return localStorage.getItem(API_KEY_STORAGE);
  } catch {
    return null;
  }
};
export const setApiKey = (key: string): void => {
  localStorage.setItem(API_KEY_STORAGE, key);
};
export const clearApiKey = (): void => {
  localStorage.removeItem(API_KEY_STORAGE);
};

/** Serialize a tRPC procedure input into the `?input=` query format. */
function encodeInput(input: unknown): string {
  return encodeURIComponent(JSON.stringify(input ?? {}));
}

async function request<T>(
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  input?: unknown
): Promise<T> {
  const apiKey = getApiKey();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
  };

  let url = `${BACKEND_URL}/trpc/${path}`;
  let body: string | undefined;

  if (method === 'GET') {
    url += `?input=${encodeInput(input)}`;
  } else {
    body = JSON.stringify(input ?? {});
  }

  const res = await fetch(url, { method, headers, body });
  const json = await res.json();

  if (!res.ok || json.error) {
    const message =
      json?.error?.message || json?.error?.data?.code || `HTTP ${res.status} ${res.statusText}`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return json.result.data as T;
}

/** Minimal typed client surface for the procedures we use. */
export const api = {
  auth: {
    whoami: () => request<{ id: string; name: string } | null>('auth.whoami', 'GET'),
  },
  workflow: {
    list: (input?: { search?: string }) =>
      request<
        Array<{
          id: string;
          name: string;
          version: number;
          createdAt: string;
          updatedAt: string;
        }>
      >('workflow.list', 'GET', input),
    get: (id: string) =>
      request<{
        id: string;
        ownerId: string | null;
        name: string;
        document: Record<string, unknown>;
        version: number;
        createdAt: string;
        updatedAt: string;
      }>('workflow.get', 'GET', { id }),
    create: (input: { name: string; document: Record<string, unknown> }) =>
      request<{ id: string; version: number }>('workflow.create', 'POST', input),
    update: (input: {
      id: string;
      name?: string;
      document?: Record<string, unknown>;
      version: number;
    }) =>
      request<{ id: string; version: number; updatedAt: string }>('workflow.update', 'POST', input),
    delete: (id: string) => request<{ ok: boolean }>('workflow.delete', 'POST', { id }),
  },
};
