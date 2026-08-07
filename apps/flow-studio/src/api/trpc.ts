/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Backend client for flow-studio → flow-backend-python.
 *
 * The Python backend exposes a REST surface (not tRPC): /api/auth/whoami,
 * /api/workflow/list, etc. This module hand-rolls a thin fetch wrapper over
 * those endpoints. The Bearer API key is read from localStorage and attached
 * to every request.
 *
 * NOTE: previously this called the Node backend's tRPC procedures under /trpc.
 * After the python-refactor migration it calls the Python backend's REST API
 * under /api. The exported `api` surface is unchanged so callers need no edits.
 */

const BACKEND_URL =
  (typeof window !== 'undefined' && window.__FLOW_BACKEND_URL__) || 'http://localhost:4001';
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

/**
 * REST request helper. GET serializes input as query params; POST/PUT/DELETE
 * send it as a JSON body. The Python backend returns data directly (no tRPC
 * envelope), so the JSON response is returned as-is.
 */
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

  let url = `${BACKEND_URL}${path}`;
  let body: string | undefined;

  if (method === 'GET') {
    // Serialize input object as query params (flat key=value pairs).
    if (input && typeof input === 'object') {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
        if (v !== undefined) params.set(k, String(v));
      }
      const qs = params.toString();
      if (qs) url += `?${qs}`;
    }
  } else {
    body = JSON.stringify(input ?? {});
  }

  const res = await fetch(url, { method, headers, body });
  const json = await res.json();

  if (!res.ok) {
    const message =
      (json && (json.detail || json.message)) || `HTTP ${res.status} ${res.statusText}`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  // Python backend returns the resource directly (FastAPI response_model).
  // A null response (e.g. whoami when unauthenticated) is valid.
  return json as T;
}

/** Minimal typed client surface — mirrors the old tRPC api shape. */
export const api = {
  auth: {
    whoami: () => request<{ id: string; name: string } | null>('/api/auth/whoami', 'GET'),
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
      >('/api/workflow/list', 'GET', input),
    get: (id: string) =>
      request<{
        id: string;
        ownerId: string | null;
        name: string;
        document: Record<string, unknown>;
        version: number;
        createdAt: string;
        updatedAt: string;
      }>('/api/workflow/get', 'GET', { id }),
    create: (input: { name: string; document: Record<string, unknown> }) =>
      request<{ id: string; version: number }>('/api/workflow/create', 'POST', input),
    update: (input: {
      id: string;
      name?: string;
      document?: Record<string, unknown>;
      version: number;
    }) =>
      request<{ id: string; version: number; updatedAt: string }>(
        '/api/workflow/update',
        'POST',
        input
      ),
    delete: (id: string) => request<{ ok: boolean }>('/api/workflow/delete', 'POST', { id }),
  },
};
