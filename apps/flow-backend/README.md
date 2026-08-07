# flow-backend (Node) — DEPRECATED

> **⚠️ This backend is deprecated.** The active backend is now
> [`apps/flow-backend-python`](../flow-backend-python/), which executes
> workflows via LangGraph (see the `feat/python-refactor` plan). This Node
> backend remains for reference and side-by-side comparison during the
> migration but is **no longer the default** — `apps/flow-studio` is wired to
> the Python backend (port 4001) as of phase 7.

## What it was

A Fastify + tRPC + Prisma server providing workflow CRUD, auth, and a runtime
execution proxy that re-exported `@flowgram.ai/runtime-nodejs` procedures.

## Why deprecated

The team's primary backend stack is Python, and the runtime execution semantics
have been redefined to follow LangGraph (stance A of the grill decisions). The
Python backend:

- Executes workflows via LangGraph (not `@flowgram.ai/runtime-js-core`)
- Shares the same MySQL database + AES-256-GCM `enc::` secret format (so
  encrypted secrets interoperate across backends)
- Exposes a REST surface under `/api/*` (not tRPC) that `flow-studio` now calls

## If you need to run it (legacy comparison)

```bash
cd apps/flow-backend
pnpm dev   # listens on :4100 (Python backend occupies :4001)
```

Do not add new features here. Migrate them to `apps/flow-backend-python` instead.
