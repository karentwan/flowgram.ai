/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Secret traversal for workflow documents.
 *
 * Secrets live inside MCP/Agent node configs at
 * `data.server.headersValues.{*}.content` (only constant-type entries hold a
 * literal secret value; ref/template entries reference upstream variables and
 * carry no plaintext). This module walks the document, encrypting those
 * constant contents on write (before persistence) and decrypting them on read
 * (before returning to the editor or handing to the runtime executor).
 * Encryption is idempotent (the crypto helper detects already-encrypted
 * values), so applying it twice is safe.
 */
import { encrypt, decrypt } from './crypto.js';

/** A flow value entry under headersValues; only `constant` carries plaintext. */
interface HeaderValue {
  type?: string;
  content?: unknown;
}

/** Minimal shape of a node we care about; the document is otherwise free-form. */
interface MaybeNode {
  type?: unknown;
  data?: unknown;
}
interface MaybeServer {
  headersValues?: Record<string, HeaderValue>;
}
interface MaybeNodeData {
  server?: MaybeServer;
}
export interface FlowDocument {
  nodes?: MaybeNode[];
  // Free-layout nests child nodes under blocks[].nodes
  blocks?: Array<{ nodes?: MaybeNode[] }>;
  [key: string]: unknown;
}

const SECRET_NODE_TYPES = new Set(['mcp', 'agent']);

function getHeaderValues(node: MaybeNode): Record<string, HeaderValue> | undefined {
  if (typeof node.type !== 'string' || !SECRET_NODE_TYPES.has(node.type)) return undefined;
  const data = node.data as MaybeNodeData | undefined;
  return data?.server?.headersValues;
}

function iterNodes(doc: FlowDocument, fn: (node: MaybeNode) => void): void {
  (doc.nodes || []).forEach(fn);
  for (const block of doc.blocks || []) {
    (block.nodes || []).forEach(fn);
  }
}

/**
 * Encrypt every constant header value in the document. Returns a deep copy —
 * the input is untouched (tRPC/zod inputs may be frozen). Call before
 * persisting to the DB. ref/template entries are skipped (no plaintext).
 */
export function encryptDocumentSecrets(doc: FlowDocument): FlowDocument {
  const next = structuredClone(doc);
  iterNodes(next, (node) => {
    const headersValues = getHeaderValues(node);
    if (!headersValues) return;
    for (const value of Object.values(headersValues)) {
      if (value?.type === 'constant' && typeof value.content === 'string' && value.content) {
        value.content = encrypt(value.content);
      }
    }
  });
  return next;
}

/**
 * Decrypt every constant header value in the document. Returns a deep copy —
 * the input is untouched (Prisma results may be frozen). Call before returning
 * a document to the editor or handing it to the executor.
 */
export function decryptDocumentSecrets(doc: FlowDocument): FlowDocument {
  const next = structuredClone(doc);
  iterNodes(next, (node) => {
    const headersValues = getHeaderValues(node);
    if (!headersValues) return;
    for (const value of Object.values(headersValues)) {
      if (value?.type === 'constant' && typeof value.content === 'string' && value.content) {
        value.content = decrypt(value.content);
      }
    }
  });
  return next;
}
