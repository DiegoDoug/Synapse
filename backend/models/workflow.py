"""Workflow models (SQLModel). Schema only — no business logic.

A ``Workflow`` is a saved automation: an ordered sequence of ``WorkflowStep``
rows (the composer — each step runs an agent or a tool) plus *when / how often*
to run it. The schedule fields are the user's personalization surface — the time
of day (cron), the repeat frequency (interval), an internal event to react to,
and an optional cap on how many times it may run before it auto-disables.

A ``WorkflowRun`` is one execution — when it ran, what triggered it (a schedule
tick, an internal event, or an on-demand click), and its outcome. Each step's
outcome is recorded as a ``WorkflowRunStep``; when a step ran an agent it carries
``agent_run_id``, linking into the Stage 6 ``AgentRun`` plan→act→observe trail
rather than duplicating it.

Status lifecycle (owned by the ``WorkflowService``):
``running`` → ``completed`` | ``failed``.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# What a workflow runs. Retained for compatibility; execution now walks the
# workflow's ``WorkflowStep`` sequence (MF2).
TARGET_AGENT = "agent"

# Kinds of step in a workflow sequence (the composer unit).
STEP_AGENT = "agent"  # run a Stage 6 domain agent
STEP_TOOL = "tool"  # run a single Stage 4/4.5 tool

# How a workflow is scheduled / triggered — the personalization surface.
SCHEDULE_MANUAL = "manual"  # only ever runs on demand (no timer)
SCHEDULE_INTERVAL = "interval"  # repeat every N minutes
SCHEDULE_CRON = "cron"  # run daily at a fixed hour:minute (UTC)
SCHEDULE_EVENT = "event"  # react to an internal event (new synced data)

# What triggered a given run.
TRIGGER_MANUAL = "manual"  # the user pressed "run now"
TRIGGER_SCHEDULE = "schedule"  # a scheduler tick fired it
TRIGGER_EVENT = "event"  # an internal event fired it

# Run lifecycle states (shared by runs and their steps).
WF_RUN_RUNNING = "running"
WF_RUN_COMPLETED = "completed"
WF_RUN_FAILED = "failed"


class Workflow(SQLModel, table=True):
    """A saved automation: a step sequence, and when / how often it runs."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    name: str
    description: str | None = Field(default=None)

    # The composed sequence lives in ``WorkflowStep`` rows. ``agent_key`` /
    # ``params`` remain as a legacy single-step shortcut: when a workflow has no
    # step rows the service synthesizes one agent step from these.
    target_kind: str = Field(default=TARGET_AGENT)
    agent_key: str = Field(default="")
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # --- Schedule / trigger personalization -------------------------------
    # manual | interval | cron | event
    schedule_kind: str = Field(default=SCHEDULE_MANUAL)
    # interval: how often it repeats.
    interval_minutes: int | None = Field(default=None)
    # cron: the time of day it runs (UTC).
    cron_hour: int | None = Field(default=None)
    cron_minute: int | None = Field(default=None)
    # event: which internal event to react to (see workflow_events.py), plus a
    # high-water mark (highest source row id already seen) so a fire only
    # happens for genuinely new synced data — never the existing backlog.
    event_type: str | None = Field(default=None)
    event_cursor: int | None = Field(default=None)
    # How many times it may run in total before it auto-disables (None = no cap).
    max_runs: int | None = Field(default=None)

    # Whether the schedule/trigger is live. Manual workflows are always disabled
    # (no timer/event) but can still be run on demand.
    enabled: bool = Field(default=False, index=True)

    # Execution tally, kept current by the service for the cap + the UI.
    run_count: int = Field(default=0)
    last_run_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowStep(SQLModel, table=True):
    """One step in a workflow's sequence: run an agent or a tool with inputs."""

    id: int | None = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)

    # Monotonic position in the sequence (stable ordering).
    step_index: int = Field(default=0)
    kind: str = Field(default=STEP_AGENT)  # agent | tool
    # The agent key or tool name to invoke.
    ref: str
    # Inputs: agent run parameters, or tool arguments.
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class WorkflowRun(SQLModel, table=True):
    """One execution of a workflow, with what triggered it and its outcome."""

    id: int | None = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    trigger: str = Field(default=TRIGGER_MANUAL)  # manual | schedule | event
    status: str = Field(default=WF_RUN_RUNNING, index=True)

    # Final result text on success, or a failure reason.
    result: str | None = Field(default=None)
    error: str | None = Field(default=None)

    # Link into the Stage 6 agent audit trail for the run's first agent step, so
    # a single-agent run stays inspectable without duplication.
    agent_run_id: int | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    finished_at: datetime | None = Field(default=None)


class WorkflowRunStep(SQLModel, table=True):
    """One step's outcome within a workflow run (the step-visibility trail)."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="workflowrun.id", index=True)

    step_index: int = Field(default=0)
    kind: str = Field(default=STEP_AGENT)  # agent | tool
    ref: str
    status: str = Field(default=WF_RUN_RUNNING)  # running | completed | failed

    # Observed output on success, or the failure reason.
    result: str | None = Field(default=None)
    error: str | None = Field(default=None)
    # The Stage 6 agent run this step drove (agent steps only).
    agent_run_id: int | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = Field(default=None)
