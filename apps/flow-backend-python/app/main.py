"""FastAPI application entry point.

Replaces ``apps/flow-backend/src/server.ts``. Hosts:
  - GET  /health  -> liveness probe (mirrors Node backend)
  - /api/*        -> workflow CRUD + auth + task execution routers (later phases)

Run with:
    uvicorn app.main:app --reload --port 4001
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth as auth_router
from app.api.routers import task as task_router
from app.api.routers import workflow as workflow_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: configure logging, then yield."""
    setup_logging()
    log = get_logger("app.main")
    settings = get_settings()
    log.info(
        "flow-backend-python starting",
        host=settings.host,
        port=settings.port,
        node_env=settings.node_env,
    )
    yield
    log.info("flow-backend-python shutting down")


def create_app() -> FastAPI:
    """Application factory (mirrors Node's createServer())."""
    settings = get_settings()

    app = FastAPI(
        title="Flowgram Studio Backend (Python)",
        description=(
            "Python backend executing FlowGram workflows via LangGraph. "
            "Replaces the Node/Fastify backend; see feat/python-refactor plan."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — same policy as Node backend (credentials + configured origins).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Liveness probe — identical payload shape to Node's /health so the editor
    # and any reverse proxy can probe either backend interchangeably.
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

    # Routers — workflow CRUD (protected) + auth (public) + task execution (public v1).
    app.include_router(workflow_router.router)
    app.include_router(auth_router.router)
    app.include_router(task_router.router)

    return app


app = create_app()
