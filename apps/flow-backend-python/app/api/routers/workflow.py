"""Workflow CRUD router — mirrors Node routers/workflow.ts.

Routes are RESTful under /api/workflow/* (NOT tRPC). Phase 7 will switch the
editor's api/trpc.ts client to call these paths. Business logic (optimistic
concurrency, secret encryption/decryption) matches Node one-for-one.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_user
from app.core.database import get_db
from app.models import Workflow
from app.utils.secrets import decrypt_document_secrets, encrypt_document_secrets

from ..schemas import (
    IdIn,
    WorkflowCreateIn,
    WorkflowCreateOut,
    WorkflowDeleteOut,
    WorkflowFull,
    WorkflowListItem,
    WorkflowUpdateIn,
    WorkflowUpdateOut,
)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


@router.get("/list", response_model=list[WorkflowListItem], response_model_by_alias=True, dependencies=[Depends(require_user)])
def list_workflows(
    user: CurrentUser = Depends(require_user),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Workflow]:
    """List the caller's workflows, newest first. Omits document body."""
    stmt = select(Workflow).where(Workflow.owner_id == user.id)
    if search:
        stmt = stmt.where(Workflow.name.contains(search))
    stmt = stmt.order_by(Workflow.updated_at.desc())
    return list(db.scalars(stmt))


@router.get("/get", response_model=WorkflowFull, response_model_by_alias=True, dependencies=[Depends(require_user)])
def get_workflow(
    id: str = Query(...),
    user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> Workflow:
    """Fetch one workflow (with document, secrets decrypted)."""
    stmt = select(Workflow).where(Workflow.id == id, Workflow.owner_id == user.id)
    wf = db.scalars(stmt).first()
    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    # Decrypt secrets in a copy so the cached ORM object stays encrypted.
    wf.document = decrypt_document_secrets(wf.document)
    return wf


@router.post("/create", response_model=WorkflowCreateOut, dependencies=[Depends(require_user)])
def create_workflow(
    payload: WorkflowCreateIn,
    user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> WorkflowCreateOut:
    """Create a workflow. Secrets in document are encrypted before persistence."""
    wf = Workflow(
        name=payload.name,
        owner_id=user.id,
        document=encrypt_document_secrets(payload.document),
        version=1,
    )
    db.add(wf)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig)) from e
    db.refresh(wf)
    return WorkflowCreateOut(id=wf.id, version=wf.version)


@router.post("/update", response_model=WorkflowUpdateOut, response_model_by_alias=True, dependencies=[Depends(require_user)])
def update_workflow(
    payload: WorkflowUpdateIn,
    user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> WorkflowUpdateOut:
    """Update a workflow with optimistic concurrency (version must match).

    Mirrors Node's updateMany-based CAS: bump version only if the row's current
    version matches the client-sent version. Stale writes → 409 CONFLICT.
    """
    stmt = select(Workflow).where(Workflow.id == payload.id, Workflow.owner_id == user.id)
    wf = db.scalars(stmt).first()
    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if wf.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stale version: current is {wf.version}, you sent {payload.version}",
        )

    if payload.name is not None:
        wf.name = payload.name
    if payload.document is not None:
        wf.document = encrypt_document_secrets(payload.document)
    wf.version += 1
    db.commit()
    db.refresh(wf)
    return WorkflowUpdateOut(id=wf.id, version=wf.version, updated_at=wf.updated_at)


@router.post("/delete", response_model=WorkflowDeleteOut, dependencies=[Depends(require_user)])
def delete_workflow(
    payload: IdIn,
    user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> WorkflowDeleteOut:
    """Delete a workflow. Idempotent on auth-scoped rows."""
    stmt = select(Workflow).where(Workflow.id == payload.id, Workflow.owner_id == user.id)
    wf = db.scalars(stmt).first()
    if wf is None:
        # Match Node: NOT_FOUND (row absent or not owned by caller).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    db.delete(wf)
    db.commit()
    return WorkflowDeleteOut(ok=True)
