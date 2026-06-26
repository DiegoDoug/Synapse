"""Workflow request/response schemas (DTOs). Mirrors backend/models/workflow.py.

Typed shapes for the automation API: the body to define or update a workflow
(its composed step sequence + schedule/trigger personalization), read views of a
workflow and of a single execution with its per-step trail, and the catalogue of
agents/tools/events the composer can pick from. Field-level constraints validate
the schedule ranges; combination rules (e.g. interval needs a frequency, event
needs a type) are checked in the service so it can return one clear message.
No business logic.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStepInput(BaseModel):
    """One composed step: run an agent or a tool with inputs."""

    kind: str = "agent"  # agent | tool
    ref: str = Field(min_length=1)  # agent key or tool name
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepRead(WorkflowStepInput):
    """Read view of a stored step (adds its position)."""

    step_index: int


class WorkflowCreate(BaseModel):
    """Body for POST /workflows — define a new automation."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    # The composed sequence. A single ``agent_key`` (+ ``params``) is still
    # accepted as a one-step shortcut for backward compatibility.
    steps: list[WorkflowStepInput] = Field(default_factory=list)
    agent_key: str | None = Field(default=None)
    params: dict[str, Any] = Field(default_factory=dict)

    # Schedule / trigger personalization.
    schedule_kind: str = "manual"
    interval_minutes: int | None = Field(default=None, ge=1, le=44640)  # ≤ 31d
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)
    event_type: str | None = None
    max_runs: int | None = Field(default=None, ge=1)
    enabled: bool = False


class WorkflowUpdate(BaseModel):
    """Body for PATCH /workflows/{id} — every field optional (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    steps: list[WorkflowStepInput] | None = None
    agent_key: str | None = Field(default=None)
    params: dict[str, Any] | None = None

    schedule_kind: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=44640)
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)
    event_type: str | None = None
    max_runs: int | None = Field(default=None, ge=1)
    enabled: bool | None = None


class WorkflowRead(BaseModel):
    """Read view of a workflow definition + its current scheduling state."""

    id: int
    name: str
    description: str | None = None
    steps: list[WorkflowStepRead] = Field(default_factory=list)

    schedule_kind: str
    interval_minutes: int | None = None
    cron_hour: int | None = None
    cron_minute: int | None = None
    event_type: str | None = None
    max_runs: int | None = None

    enabled: bool
    run_count: int
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowRunStepRead(BaseModel):
    """Read view of one step's outcome within a run."""

    id: int
    step_index: int
    kind: str
    ref: str
    status: str  # running | completed | failed
    result: str | None = None
    error: str | None = None
    agent_run_id: int | None = None


class WorkflowRunRead(BaseModel):
    """Read view of a single workflow execution + its per-step trail."""

    id: int
    workflow_id: int
    trigger: str  # manual | schedule | event
    status: str  # running | completed | failed
    result: str | None = None
    error: str | None = None
    agent_run_id: int | None = None
    steps: list[WorkflowRunStepRead] = Field(default_factory=list)
    created_at: datetime
    finished_at: datetime | None = None


# --- Catalogue (what the composer can pick from) -----------------------------


class CatalogueParam(BaseModel):
    name: str
    description: str | None = None
    required: bool = False


class CatalogueEntry(BaseModel):
    """An agent or tool the composer can add as a step."""

    kind: str  # agent | tool
    ref: str
    name: str
    description: str
    parameters: list[CatalogueParam] = Field(default_factory=list)


class CatalogueEvent(BaseModel):
    """An internal event a workflow can be triggered by."""

    event_type: str
    label: str


class WorkflowCatalogue(BaseModel):
    """Everything the composer UI needs to build a workflow."""

    steps: list[CatalogueEntry] = Field(default_factory=list)
    events: list[CatalogueEvent] = Field(default_factory=list)
