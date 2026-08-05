/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Workflow CRUD router (protected — requires a Bearer API key).
 *
 * - Secrets in `document` are encrypted on write, decrypted on read.
 * - `update` uses optimistic concurrency: clients send the `version` they
 *   loaded; stale writes are rejected with CONFLICT.
 * - `list` omits the (potentially large) document body; fetch `get` for the doc.
 */
import { z } from 'zod';
import { TRPCError } from '@trpc/server';

import { protectedProcedure, router } from '../trpc.js';
import { encryptDocumentSecrets, decryptDocumentSecrets } from '../lib/secrets.js';
import { prisma } from '../db.js';

const documentSchema = z.record(z.any());

export const workflowRouter = router({
  list: protectedProcedure
    .input(z.object({ search: z.string().optional() }).optional())
    .query(({ ctx, input }) =>
      prisma.workflow.findMany({
        where: {
          ownerId: ctx.user.id,
          ...(input?.search ? { name: { contains: input.search } } : {}),
        },
        select: {
          id: true,
          name: true,
          version: true,
          createdAt: true,
          updatedAt: true,
        },
        orderBy: { updatedAt: 'desc' },
      })
    ),

  get: protectedProcedure.input(z.object({ id: z.string() })).query(async ({ ctx, input }) => {
    const wf = await prisma.workflow.findFirst({
      where: { id: input.id, ownerId: ctx.user.id },
    });
    if (!wf) throw new TRPCError({ code: 'NOT_FOUND' });
    return {
      ...wf,
      document: decryptDocumentSecrets(wf.document as never),
    };
  }),

  create: protectedProcedure
    .input(z.object({ name: z.string().min(1), document: documentSchema }))
    .mutation(async ({ ctx, input }) => {
      const wf = await prisma.workflow.create({
        data: {
          name: input.name,
          ownerId: ctx.user.id,
          document: encryptDocumentSecrets(input.document) as never,
        },
      });
      return { id: wf.id, version: wf.version };
    }),

  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).optional(),
        document: documentSchema.optional(),
        version: z.number().int(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Optimistic concurrency: bump version only if the row's version matches.
      const encryptedDoc = input.document
        ? (encryptDocumentSecrets(input.document) as never)
        : undefined;
      try {
        const updated = await prisma.workflow.updateMany({
          where: { id: input.id, ownerId: ctx.user.id, version: input.version },
          data: {
            ...(input.name ? { name: input.name } : {}),
            ...(encryptedDoc ? { document: encryptedDoc } : {}),
            version: { increment: 1 },
          },
        });
        if (updated.count === 0) {
          // Either not found/forbidden, or version mismatch (stale write).
          const existing = await prisma.workflow.findFirst({
            where: { id: input.id, ownerId: ctx.user.id },
            select: { version: true },
          });
          if (!existing) throw new TRPCError({ code: 'NOT_FOUND' });
          throw new TRPCError({
            code: 'CONFLICT',
            message: `Stale version: current is ${existing.version}, you sent ${input.version}`,
          });
        }
      } catch (e) {
        if (e instanceof TRPCError) throw e;
        throw new TRPCError({ code: 'INTERNAL_SERVER_ERROR', cause: e });
      }
      const wf = await prisma.workflow.findFirst({
        where: { id: input.id },
        select: { id: true, version: true, updatedAt: true },
      });
      return { id: wf!.id, version: wf!.version, updatedAt: wf!.updatedAt };
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const deleted = await prisma.workflow.deleteMany({
        where: { id: input.id, ownerId: ctx.user.id },
      });
      if (deleted.count === 0) throw new TRPCError({ code: 'NOT_FOUND' });
      return { ok: true };
    }),
});
