/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Root tRPC router: merges product routers (auth, workflow) with the runtime
 * execution router (task.run, task.validate, ...).
 *
 * The runtime router is SPREAD at the root (not nested under `runtime:`) so
 * its procedures resolve at their OpenAPI paths — the editor's server-mode
 * client calls `/api/task/run` etc., and the OpenAPI plugin maps those to the
 * root-level `task/run` procedure. Nesting under `runtime:` would make them
 * `runtime/task.run`, which the client never calls.
 */
import { router } from './trpc.js';
import { workflowRouter } from './routers/workflow.js';
import { runtimeRouter } from './routers/runtime.js';
import { authRouter } from './routers/auth.js';

export const appRouter = router({
  auth: authRouter,
  workflow: workflowRouter,
  ...runtimeRouter._def.procedures,
});

export type AppRouter = typeof appRouter;
