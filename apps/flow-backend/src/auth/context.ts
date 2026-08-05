/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * tRPC request context: resolves the caller from the `Authorization: Bearer
 * <apiKey>` header. Returns `user: null` when no/invalid token — protected
 * procedures then reject; public procedures proceed.
 */
import { CreateFastifyContextOptions } from '@trpc/server/adapters/fastify';

import { prisma } from '../db.js';

export interface User {
  id: string;
  name: string;
}

export interface AppContext {
  user: User | null;
}

export async function createContext({ req }: CreateFastifyContextOptions): Promise<AppContext> {
  const header = req.headers.authorization;
  if (!header || !header.toLowerCase().startsWith('bearer ')) {
    return { user: null };
  }
  const token = header.slice(7).trim();
  if (!token) return { user: null };

  const user = await prisma.user.findUnique({
    where: { apiKey: token },
    select: { id: true, name: true },
  });
  return { user };
}
