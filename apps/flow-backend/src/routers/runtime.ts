/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Execution proxy: re-export the nodejs runtime's appRouter so the editor can
 * hit ONE tRPC endpoint for both CRUD (`workflow.*`, `auth.*`) and execution
 * (`task.run`, `task.validate`, `task.cancel`, ...).
 *
 * The runtime's executors (MCPExecutor, AgentExecutor, etc.) run here, on the
 * server — so MCP/Agent calls go out from Node, not the browser (no CORS, and
 * secrets in the decrypted document never leave the server).
 *
 * We re-export the runtime router verbatim (no wrapping) to preserve its
 * procedure shapes; it's merged into the root router in `src/trpc-root.ts`.
 *
 * NOTE: the runtime procedures are currently public (the runtime has no auth).
 * Wrapping them behind `protectedProcedure` requires re-declaring each
 * procedure; that's a follow-up. For v1 we rely on the Fastify layer /
 * deployment network to gate access.
 */
export { appRouter as runtimeRouter } from '@flowgram.ai/runtime-nodejs';
