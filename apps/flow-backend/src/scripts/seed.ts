/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Seed script: creates a user and prints their API key.
 *
 * Usage:
 *   pnpm seed                       # creates/updates the default user
 *   pnpm seed -- --name Alice       # creates a user named Alice
 *
 * The printed API key is the Bearer token the editor stores in localStorage.
 * Re-running with the same name is idempotent (keeps the existing key).
 */
import { randomBytes } from 'node:crypto';

import { prisma } from '../db.js';

async function main() {
  const nameIdx = process.argv.indexOf('--name');
  const name = nameIdx !== -1 ? process.argv[nameIdx + 1] : 'admin';

  const existing = await prisma.user.findFirst({ where: { name } });
  if (existing) {
    console.log(
      `User "${name}" already exists.\n  id: ${existing.id}\n  apiKey: ${existing.apiKey}`
    );
    return;
  }

  const apiKey = `fk_${randomBytes(24).toString('hex')}`;
  const user = await prisma.user.create({ data: { name, apiKey } });

  console.log(
    `Created user "${user.name}".\n  id: ${user.id}\n  apiKey: ${user.apiKey}\n\nStore this key; it will not be shown again.`
  );
}

main()
  .catch((e) => {
    console.error('Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
