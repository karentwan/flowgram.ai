/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Flowgram Studio backend configuration.
 * All values come from environment variables; see .env.example.
 */

export const config = {
  port: Number(process.env.PORT ?? 4000),
  host: process.env.HOST ?? '0.0.0.0',
  databaseUrl: process.env.DATABASE_URL ?? '',
  /**
   * 32-byte master key (base64) used to encrypt secrets at rest in workflow
   * documents (MCP/Agent node `server.headersValues.{*}.content` for constant
   * entries). Generate one with:
   *   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   */
  encryptionKey: process.env.FLOWGRAM_ENCRYPTION_KEY ?? '',
  /** Allowed origin for the editor SPA (CORS). Use the deployed studio URL. */
  corsOrigin: (process.env.CORS_ORIGIN ?? 'http://localhost:3000').split(','),
  nodeEnv: process.env.NODE_ENV ?? 'development',
} as const;
