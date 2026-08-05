/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Root tRPC router: merges product routers (auth, workflow) with the runtime
 * execution router (task.run, task.validate, ...).
 */
import { router } from './trpc.js';
import { workflowRouter } from './routers/workflow.js';
import { runtimeRouter } from './routers/runtime.js';
import { authRouter } from './routers/auth.js';

export const appRouter = router({
  auth: authRouter,
  workflow: workflowRouter,
  /**
   * Spread the runtime router's procedures at the root so paths like
   * `task.run` resolve (the runtime defines procedures at paths such as
   * `/task/run`, served at `/trpc/task.run`). Runtime procedures remain public.
   */
  runtime: runtimeRouter,
});

export type AppRouter = typeof appRouter;
