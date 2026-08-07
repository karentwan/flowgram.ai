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
