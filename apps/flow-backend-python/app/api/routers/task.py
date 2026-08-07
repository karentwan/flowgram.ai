"""Task execution router — mirrors Node's task.* procedures.

Endpoints (paths align with Node's OpenAPI definitions):
  POST /api/task/run       {schema, inputs}          → {taskID}
  GET  /api/task/result    ?taskID=                   → outputs | null
  GET  /api/task/report    ?taskID=                   → report | null
  PUT  /api/task/cancel    {taskID}                   → {success}
  POST /api/task/validate  {schema, inputs}           → {valid, errors?}

Note: Node exposes these as public (no auth) in v1; we match that here.
Phase 7 may add auth when the editor is switched over.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.engine.loader import IRLoaderError, load_ir
from app.engine.runner import get_task_manager

router = APIRouter(prefix="/api/task", tags=["task"])


# --------------------------------------------------------------------------
# Request / response schemas
# --------------------------------------------------------------------------


class TaskRunIn(BaseModel):
    schema_: str = Field(..., alias="schema")
    inputs: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class TaskRunOut(BaseModel):
    taskID: str


class TaskCancelIn(BaseModel):
    taskID: str


class TaskCancelOut(BaseModel):
    success: bool


class TaskValidateIn(BaseModel):
    schema_: str = Field(..., alias="schema")
    inputs: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class TaskValidateOut(BaseModel):
    valid: bool
    errors: list[str] | None = None


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.post("/run", response_model=TaskRunOut)
async def task_run(payload: TaskRunIn) -> TaskRunOut:
    """Build the graph and start execution. Returns the task id immediately."""
    schema_obj = json.loads(payload.schema_)
    task_id = get_task_manager().run(schema_obj, payload.inputs)
    return TaskRunOut(taskID=task_id)


@router.get("/result")
def task_result(taskID: str = Query(...)) -> dict[str, Any] | None:
    """Return final outputs if terminated, else None."""
    return get_task_manager().result(taskID)


@router.get("/report")
def task_report(taskID: str = Query(...)) -> dict[str, Any] | None:
    """Return the current execution report (status + per-node status)."""
    return get_task_manager().report(taskID)


@router.put("/cancel", response_model=TaskCancelOut)
def task_cancel(payload: TaskCancelIn) -> TaskCancelOut:
    """Request task cancellation."""
    return TaskCancelOut(success=get_task_manager().cancel(payload.taskID))


@router.post("/validate", response_model=TaskValidateOut)
def task_validate(payload: TaskValidateIn) -> TaskValidateOut:
    """Validate a workflow schema without executing it."""
    try:
        load_ir(payload.schema_)
    except IRLoaderError as e:
        return TaskValidateOut(valid=False, errors=[str(e)])
    return TaskValidateOut(valid=True)
