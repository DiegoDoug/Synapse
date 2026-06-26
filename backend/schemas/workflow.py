"""Workflow request/response schemas (DTOs). Mirrors backend/models/workflow.py.

Typed shapes for the automation API: the body to define or update a workflow
(including its schedule personalization), and read views of a workflow and of a
single execution. Field-level constraints validate the schedule ranges; the
required-field combinations (e.g. interval needs a frequency) are checked in the
service so it can return a single clear message. No business logic.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Mirrored from the model so the API and the frontend share one vocabulary.
ScheduleKind = str  # manual | interval | cron


class WorkflowCreate(BaseModel):
    """Body for POST /workflows — define a new automation."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    agent_key: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    # Schedule personalization (validated for combination-consistency in the
    # service). Ranges are enforced here.
    schedule_kind: str = "manual"
    interval_minutes: int | None = Field(default=None, ge=1, le=44640)  # ≤ 31d
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)
    max_runs: int | None = Field(default=None, ge=1)
    enabled: bool = False


class WorkflowUpdate(BaseModel):
    """Body for PATCH /workflows/{id} — every field optional (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    agent_key: str | None = Field(default=None, min_length=1)
    params: dict[str, Any] | None = None

    schedule_kind: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=44640)
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)
    max_runs: int | None = Field(default=None, ge=1)
    enabled: bool | None = None


class WorkflowRead(BaseModel):
    """Read view of a workflow definition + its current scheduling state."""

    id: int
    name: str
    description: str | None = None
    target_kind: str
    agent_key: str
    params: dict[str, Any] = Field(default_factory=dict)

    schedule_kind: str
    interval_minutes: int | None = None
    cron_hour: int | None = None
    cron_minute: int | None = None
    max_runs: int | None = None

    enabled: bool
    run_count: int
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowRunRead(BaseModel):
    """Read view of a single workflow execution."""

    id: int
    workflow_id: int
    trigger: str  # manual | schedule
    status: str  # running | completed | failed
    result: str | None = None
    error: str | None = None
    agent_run_id: int | None = None
    created_at: datetime
    finished_at: datetime | None = None
