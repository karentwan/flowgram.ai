/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Fastify server. Hosts the tRPC appRouter (auth + workflow CRUD + runtime
 * execution) under `/trpc`, plus a `/health` check.
 *
 * CORS allows the configured editor origin(s) so the studio SPA can call us
 * cross-origin during development; in production we expect a reverse proxy to
 * serve both under one origin.
 */
import fastify from 'fastify';
import { fastifyTRPCPlugin } from '@trpc/server/adapters/fastify';
import cors from '@fastify/cors';

import { appRouter } from './trpc-root.js';
import { config } from './config.js';
import { createContext } from './auth/context.js';

export async function createServer() {
  const server = fastify({ logger: config.nodeEnv === 'development' });

  await server.register(cors, {
    origin: config.corsOrigin,
    credentials: true,
  });

  await server.register(fastifyTRPCPlugin, {
    prefix: '/trpc',
    trpcOptions: { router: appRouter, createContext },
  });

  server.get('/health', async () => ({ status: 'ok', time: new Date().toISOString() }));

  const start = async () => {
    await server.listen({ port: config.port, host: config.host });

    console.log(`> flow-backend listening on http://${config.host}:${config.port}`);
  };
  const stop = async () => server.close();

  return { server, start, stop };
}
