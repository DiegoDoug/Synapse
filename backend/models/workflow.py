"""Workflow + WorkflowRun models (SQLModel). Schema only — no business logic.

A ``Workflow`` is a saved automation: *what* to run (a Stage 6 agent, for now)
and *when / how often* to run it. The schedule fields are the user's
personalization surface — the time of day (cron), the repeat frequency
(interval), and an optional cap on how many times it may run before it
auto-disables.

A ``WorkflowRun`` is one execution of a workflow — when it ran, what triggered
it (a schedule tick or an on-demand click), and its outcome. When the workflow
ran an agent it carries ``agent_run_id``, linking into the Stage 6 ``AgentRun``
plan→act→observe audit trail rather than duplicating it.

Status lifecycle (owned by the ``WorkflowService``):
``running`` → ``completed`` | ``failed``.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# What a workflow runs. Stage 7 MF1 supports a single agent run; MF2 extends
# this to multi-step tool/agent sequences.
TARGET_AGENT = "agent"

# How a workflow is scheduled — the personalization surface.
SCHEDULE_MANUAL = "manual"  # only ever runs on demand (no timer)
SCHEDULE_INTERVAL = "interval"  # repeat every N minutes
SCHEDULE_CRON = "cron"  # run daily at a fixed hour:minute (UTC)

# What triggered a given run.
TRIGGER_MANUAL = "manual"  # the user pressed "run now"
TRIGGER_SCHEDULE = "schedule"  # a scheduler tick fired it

# Run lifecycle states.
WF_RUN_RUNNING = "running"
WF_RUN_COMPLETED = "completed"
WF_RUN_FAILED = "failed"


class Workflow(SQLModel, table=True):
    """A saved automation: what to run, and when / how often."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    name: str
    description: str | None = Field(default=None)

    # What runs. MF1: a single agent identified by its registry key, with the
    # input parameters to start it with.
    target_kind: str = Field(default=TARGET_AGENT)
    agent_key: str
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # --- Schedule personalization -----------------------------------------
    # manual | interval | cron
    schedule_kind: str = Field(default=SCHEDULE_MANUAL)
    # interval: how often it repeats.
    interval_minutes: int | None = Field(default=None)
    # cron: the time of day it runs (UTC).
    cron_hour: int | None = Field(default=None)
    cron_minute: int | None = Field(default=None)
    # How many times it may run in total before it auto-disables (None = no cap).
    max_runs: int | None = Field(default=None)

    # Whether the schedule is live. Manual workflows are always disabled (they
    # have no timer) but can still be run on demand.
    enabled: bool = Field(default=False, index=True)

    # Execution tally, kept current by the service for the cap + the UI.
    run_count: int = Field(default=0)
    last_run_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowRun(SQLModel, table=True):
    """One execution of a workflow, with what triggered it and its outcome."""

    id: int | None = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    trigger: str = Field(default=TRIGGER_MANUAL)  # manual | schedule
    status: str = Field(default=WF_RUN_RUNNING, index=True)

    # Final result text on success, or a failure reason.
    result: str | None = Field(default=None)
    error: str | None = Field(default=None)

    # Link into the Stage 6 agent audit trail when this run drove an agent, so
    # the run's plan→act→observe steps stay inspectable without duplication.
    agent_run_id: int | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    finished_at: datetime | None = Field(default=None)
