/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Auth router.
 *
 * v1 keeps auth intentionally simple: the API key IS the credential. There is
 * no password login — keys are minted by the seed script (`pnpm seed`) and
 * passed to the editor, which stores them in localStorage and sends them as a
 * Bearer header. `whoami` lets the editor verify a stored key on startup.
 */
import { publicProcedure, router } from '../trpc.js';

export const authRouter = router({
  /** Returns the caller's user if their Bearer token is valid, else null. */
  whoami: publicProcedure.query(({ ctx }) => ctx.user),
});
