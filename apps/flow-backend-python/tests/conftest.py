"""Test fixtures: in-memory SQLite DB + fixed encryption key.

The Python backend normally shares MySQL with the Node backend, but for tests
we inject an in-memory SQLite engine created from the ORM models (the models
mirror the production schema, so CRUD logic is equivalent).
"""

from __future__ import annotations

import base64
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Fixed key so encrypt/decrypt run during tests (must be valid 32-byte base64).
TEST_KEY_B64 = base64.b64encode(b"K" * 32).decode()


@pytest.fixture(autouse=True)
def _set_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a fixed encryption key for all tests."""
    monkeypatch.setenv("FLOWGRAM_ENCRYPTION_KEY", TEST_KEY_B64)
    from app.core import config

    config.get_settings.cache_clear()


@pytest.fixture
def sqlite_engine():
    """An isolated in-memory SQLite engine with the ORM schema created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    from app.models import Base

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine) -> Generator[Session, None, None]:
    """A session bound to the in-memory engine (for direct DB assertions)."""
    from app.core import database

    database.configure_engine(sqlite_engine)
    session = database.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(sqlite_engine) -> Generator[TestClient, None, None]:
    """A TestClient whose get_db dependency uses the in-memory engine."""
    from app.core import database

    database.configure_engine(sqlite_engine)

    from app.main import app

    yield TestClient(app)


@pytest.fixture
def seed_user(db_session: Session) -> tuple[str, str]:
    """Seed a user and return (user_id, api_key)."""
    from app.models import User

    user = User(id="u_test", name="tester", api_key="fk_test_key_123")
    db_session.add(user)
    db_session.commit()
    return user.id, user.api_key


@pytest.fixture
def auth_headers(seed_user: tuple[str, str]) -> dict[str, str]:
    """Bearer auth headers for the seeded user."""
    _, api_key = seed_user
    return {"Authorization": f"Bearer {api_key}"}
