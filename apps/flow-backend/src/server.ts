/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Fastify server. Hosts the tRPC appRouter (auth + workflow CRUD + runtime
 * execution) under `/trpc`, plus a `/health` check.
 *
 * The OpenAPI plugin exposes the runtime procedures as REST endpoints under
 * `/api` (e.g. POST /api/task/run) — the editor's server-mode runtime client
 * calls those paths, not the tRPC ones. CORS allows the configured editor
 * origin(s); in production we expect a reverse proxy to serve both under one
 * origin.
 */
import { fastifyTRPCOpenApiPlugin } from 'trpc-openapi';
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

  // Expose runtime procedures (task/run, task/report, ...) as REST endpoints
  // under /api so the editor's server-mode client can reach them. Cast as any
  // to match runtime-nodejs' usage — the plugin type wants optional handlers we
  // don't customize.
  await server.register(fastifyTRPCOpenApiPlugin, {
    basePath: '/api',
    router: appRouter,
    createContext,
  } as any);

  server.get('/health', async () => ({ status: 'ok', time: new Date().toISOString() }));

  const start = async () => {
    await server.listen({ port: config.port, host: config.host });

    console.log(`> flow-backend listening on http://${config.host}:${config.port}`);
  };
  const stop = async () => server.close();

  return { server, start, stop };
}
