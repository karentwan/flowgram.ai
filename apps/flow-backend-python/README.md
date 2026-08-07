# flow-backend-python

Python backend for Flowgram Workflow Studio. Executes workflows via **LangGraph** instead of the Node `@flowgram.ai/runtime-js-core` engine. This is the target backend; the legacy Node backend lives at `apps/flow-backend` and will be deprecated once feature parity is reached.

See the `feat/python-refactor` plan for the full architecture contract (stances, invariants, migration phases).

## Status

**Phase 0 — scaffolding.** Only `/health` is wired. Subsequent phases add:
- Phase 1: LangGraph IR schema (canvas → Python contract)
- Phase 2: CRUD + auth + AES-256-GCM crypto (Node `enc::` compat)
- Phase 3: LangGraph execution engine + core node executors
- Phase 4: Loop node concurrency (serial/parallel + break sugar) ← grill core need
- Phase 5: MCP + Agent nodes
- Phase 6: Observability (structlog + PostgresSaver + stats tables)
- Phase 7: Editor cutover + Node backend deprecation

## Stack

| Concern | Choice |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Execution engine | LangGraph (semantic authority — see plan "stance A") |
| LLM | langchain-openai |
| MCP | langchain-mcp-adapters |
| DB | SQLAlchemy + Alembic (shares DB with Node/Prisma backend) |
| Crypto | `cryptography` (AES-256-GCM, `enc::` format compat with Node) |
| Logging | structlog (JSON) |
| Python | ≥ 3.11 |

## Quickstart

```bash
cd apps/flow-backend-python
cp .env.example .env       # fill in FLOWGRAM_ENCRYPTION_KEY, DATABASE_URL
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run
uvicorn app.main:app --reload --port 4001

# Verify
curl http://localhost:4001/health
# -> {"status":"ok","time":"2026-08-07T..."}
```

## Port

Defaults to **4001** so it can run side-by-side with the Node backend (4000) during the migration. Override with `PORT=` in `.env`.

## Architecture invariants (from grill)

1. **Stance A**: semantic authority is LangGraph; FlowGram invents no execution semantics.
2. **Canvas fields**: only performance hints that don't affect LangGraph semantics (e.g. loop `mode`/`semaphore`).
3. **Variable refs (V1)**: canvas UI stays node-centric; serialization translates to flat State fields `{nodeId}__{fieldName}`.
4. **Code node**: Python only (dev `exec`, prod sandbox TBD).
5. **Crypto**: `enc::` AES-256-GCM payloads must decrypt across Node and Python backends.
6. **Observability (route 2)**: structlog + PostgresSaver + stats tables; no third-party SaaS; post-hoc query (no streaming).
