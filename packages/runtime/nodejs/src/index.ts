/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

// Re-export the tRPC appRouter + type so downstream apps (e.g. flow-backend)
// can merge the runtime's execution procedures into their own root router.
export { appRouter, type AppRouter } from '@api/index';
export { createServer } from '@server/index';

// Keep backwards-compatible direct startup when run as a standalone process
// (e.g. `pnpm start` / `node dist/index.js`). Guarded so importing the module
// for its exports does not start a server.
if (import.meta.url === `file://${process.argv[1]}`) {
  import('@server/index').then(async ({ createServer }) => {
    const server = await createServer();
    server.start();
  });
}
