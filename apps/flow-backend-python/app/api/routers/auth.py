"""Auth router — mirrors Node routers/auth.ts.

`whoami` returns the caller's user if their Bearer token is valid, else null.
This is a public endpoint (no 401 — unauthenticated callers get null).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, resolve_user

from ..schemas import WhoamiOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/whoami", response_model=WhoamiOut | None)
async def whoami(user: CurrentUser | None = Depends(resolve_user)) -> WhoamiOut | None:
    """Return the resolved user, or null if no/invalid Bearer token."""
    if user is None:
        return None
    return WhoamiOut(id=user.id, name=user.name)
