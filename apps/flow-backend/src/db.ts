/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Prisma client singleton.
 */
import { PrismaClient } from '@prisma/client';

export const prisma = new PrismaClient();
