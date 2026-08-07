"""Pydantic request/response schemas for the workflow CRUD API.

Mirrors the shapes Node's tRPC procedures accept/return (see
apps/flow-studio/src/api/trpc.ts `api.workflow.*` signatures).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Workflow
# --------------------------------------------------------------------------


class WorkflowListItem(BaseModel):
    """list() row — document body omitted (potentially large)."""

    id: str
    name: str
    version: int
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class WorkflowFull(WorkflowListItem):
    """get() row — includes document + ownerId."""

    owner_id: str | None = Field(default=None, alias="ownerId")
    document: dict[str, Any]


class WorkflowCreateIn(BaseModel):
    name: str = Field(min_length=1)
    document: dict[str, Any]


class WorkflowCreateOut(BaseModel):
    id: str
    version: int


class WorkflowUpdateIn(BaseModel):
    id: str
    name: str | None = Field(default=None, min_length=1)
    document: dict[str, Any] | None = None
    version: int  # optimistic concurrency


class WorkflowUpdateOut(BaseModel):
    id: str
    version: int
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class WorkflowDeleteIn(BaseModel):
    id: str


class WorkflowDeleteOut(BaseModel):
    ok: bool = True


class IdIn(BaseModel):
    """Generic {id} body used by delete-style endpoints."""

    id: str


class WorkflowListIn(BaseModel):
    search: str | None = None


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class WhoamiOut(BaseModel):
    """whoami response — null when unauthenticated (mirrors Node ctx.user)."""

    id: str
    name: str
