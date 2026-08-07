"""Auth: Bearer API key resolution — mirrors Node auth/context.ts + trpc.ts.

The API key is the credential (plain-text, v1 design). It's matched against
``User.api_key`` via the unique index. ``resolve_user`` returns the user or
``None`` (public endpoints proceed; protected endpoints raise 401).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User


@dataclass
class CurrentUser:
    """The resolved caller. Shape matches Node's `User` ({id, name})."""

    id: str
    name: str


def _extract_bearer_token(request: Request) -> str | None:
    """Extract the token from `Authorization: Bearer <token>`. Mirrors createContext."""
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()  # len("bearer ") == 7
    return token or None


async def resolve_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser | None:
    """Resolve the caller from the Bearer header. Returns None if no/invalid token."""
    token = _extract_bearer_token(request)
    if not token:
        return None
    stmt = select(User).where(User.api_key == token).with_only_columns(User.id, User.name)
    row = db.execute(stmt).first()
    if row is None:
        return None
    return CurrentUser(id=row.id, name=row.name)


async def require_user(user: CurrentUser | None = Depends(resolve_user)) -> CurrentUser:
    """Protected-endpoint dependency: raises 401 if not authenticated.

    Mirrors Node's protectedProcedure middleware.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return user
