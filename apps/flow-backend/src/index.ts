/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * flow-backend entry point.
 */
import { createServer } from './server.js';

async function main() {
  const server = await createServer();
  await server.start();
}

main().catch((err) => {
  console.error('Failed to start flow-backend:', err);
  process.exit(1);
});
