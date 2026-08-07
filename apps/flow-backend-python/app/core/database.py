"""Database session + engine.

Shares the same database as the Node/Prisma backend (DATABASE_URL). We do NOT
run migrations from Python — the schema is owned by
`apps/flow-backend/prisma/init.sql` (run it once against MySQL). SQLAlchemy
here is read/write against the existing tables only.

Engine creation is **lazy** so importing this module (and thus the app) does
not require DATABASE_URL to be set — important for tests and for booting the
app before the DB is configured (e.g. `--help`, `/health` only).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _validate_url(url: str) -> str:
    """Ensure DATABASE_URL is usable by SQLAlchemy.

    MySQL URLs from Prisma look like `mysql://user:pass@host:port/db` which
    SQLAlchemy accepts directly. An empty URL means the DB isn't configured yet.
    """
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it in .env "
            "(e.g. mysql://flowgram:flowgram@localhost:3306/flowgram)."
        )
    return url


def get_engine() -> Engine:
    """Return the lazily-created singleton engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(_validate_url(settings.database_url), pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the lazily-created session factory bound to the engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, class_=Session)
    return _SessionLocal


def configure_engine(engine: Engine) -> None:
    """Override the engine (used by tests to inject an in-memory SQLite engine)."""
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session, closes it after the request."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
