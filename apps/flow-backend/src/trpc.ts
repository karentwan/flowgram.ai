/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * tRPC instance + middleware.
 *
 * `publicProcedure` is open; `protectedProcedure` requires a valid Bearer API
 * key (resolves `ctx.user`). Procedures that scope workflow data use the latter
 * and filter by `ctx.user.id`.
 */
import { initTRPC, TRPCError } from '@trpc/server';

import type { AppContext } from './auth/context.js';

const t = initTRPC.context<AppContext>().create();

export const router = t.router;
export const publicProcedure = t.procedure;

export const protectedProcedure = t.procedure.use(({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED', message: 'Missing or invalid API key' });
  }
  return next({ ctx: { ...ctx, user: ctx.user } });
});
