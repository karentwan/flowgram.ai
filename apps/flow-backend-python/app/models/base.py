"""SQLAlchemy ORM models mirroring `apps/flow-backend/prisma/init.sql`.

The Python backend shares the SAME MySQL database as the Node/Prisma backend,
so column names are kept in camelCase (matching the DDL) via explicit
`Column("camelCaseName")` mappings. Python attributes use snake_case.

Schema changes MUST be made in `prisma/init.sql` first (the source of truth),
then reflected here. Python does not run migrations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""


def _cuid() -> str:
    """Generate a cuid-like id matching Prisma's `@default(cuid())` format.

    Prisma cuid() is base36-encoded with a fixed prefix; we approximate with a
    24-char hex prefixed `c` to stay within the VARCHAR(191) column and keep IDs
    globally unique. (The exact format doesn't matter — uniqueness does, and the
    Node backend already accepts any VARCHAR id.)
    """
    import secrets

    return "c" + secrets.token_hex(12)  # 25 chars total, fits VARCHAR(191)


class User(Base):
    """A studio user. Auth is plain-text API key (Bearer token). Mirrors `User` table."""

    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String(191), primary_key=True, default=_cuid)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    # Plain-text API key (v1 design — see schema.prisma comment). Bearer token
    # is matched against this column via the unique index.
    api_key: Mapped[str] = mapped_column("apiKey", String(191), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    workflows: Mapped[list[Workflow]] = relationship(back_populates="owner")


class Workflow(Base):
    """A saved workflow. `document` holds the full FlowDocumentJSON. Mirrors `Workflow` table."""

    __tablename__ = "Workflow"

    id: Mapped[str] = mapped_column(String(191), primary_key=True, default=_cuid)
    owner_id: Mapped[str | None] = mapped_column(
        "ownerId", String(191), ForeignKey("User.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    # Stored as MySQL JSON; SQLAlchemy JSON dialect handles (de)serialization.
    document: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    # `onupdate=func.now()` mirrors MySQL `ON UPDATE CURRENT_TIMESTAMP(3)`.
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped[User | None] = relationship(back_populates="workflows")


class TaskRun(Base):
    """Execution record for observability (grill route 2: business stats table).

    One row per task run. Stores final status, token totals, duration, and a
    snapshot of the final State (for post-hoc replay — replaces LangGraph's
    PostgresSaver which is Postgres-only and we're on MySQL).
    """

    __tablename__ = "TaskRun"

    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    inputs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outputs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    state_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        "stateSnapshot", JSON, nullable=True
    )
    # Aggregate token usage across all LLM/agent calls in this run.
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column("durationMs", Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    nodes: Mapped[list[NodeExecution]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class NodeExecution(Base):
    """Per-node execution record (child of TaskRun).

    One row per node invocation. For loops, one row per iteration (indexed).
    Captures status, duration, inputs/outputs, and token usage (LLM/agent only).
    """

    __tablename__ = "NodeExecution"

    id: Mapped[str] = mapped_column(String(191), primary_key=True, default=_cuid)
    task_id: Mapped[str] = mapped_column(
        "taskId", String(191), ForeignKey("TaskRun.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column("nodeId", String(191), nullable=False)
    node_type: Mapped[str] = mapped_column("nodeType", String(64), nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    inputs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outputs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column("durationMs", Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        "startedAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    task: Mapped[TaskRun] = relationship(back_populates="nodes")
