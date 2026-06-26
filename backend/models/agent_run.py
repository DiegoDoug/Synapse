"""AgentRun + AgentStep models (SQLModel). Schema only — no business logic.

An ``AgentRun`` is one execution of a domain agent: which agent ran, the input
it was given, its status, and the final result. Each ``AgentStep`` is a single
entry in that run's plan→act→observe trail — the agent's plan, every tool it
invoked and what it observed back, the final result, or a failure. Together they
form the Stage 6 audit trail: a run records its reasoning and any destructive
action it routed through the confirmation flow.

Status lifecycle (owned by the ``AgentRunner``):
``running`` → ``completed`` | ``failed``.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# Run lifecycle states.
RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"

# Step kinds — the phases of the plan→act→observe loop.
STEP_PLAN = "plan"  # the agent's intended approach, recorded before acting
STEP_ACTION = "action"  # one tool invocation and the result it observed
STEP_RESULT = "result"  # the agent's final composed output
STEP_ERROR = "error"  # a failure that ended the run

# Step outcome flags.
STEP_OK = "ok"
STEP_FAILED = "failed"


class AgentRun(SQLModel, table=True):
    """One execution of an agent, with its status and final outcome."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    # Which agent ran (stable key) and its display name at run time.
    agent_key: str = Field(index=True)
    agent_name: str

    # The input parameters the run was started with (provider-neutral JSON).
    input: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    status: str = Field(default=RUN_RUNNING, index=True)
    # Final assistant-facing result text on success, or a failure reason.
    result: str | None = Field(default=None)
    error: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    finished_at: datetime | None = Field(default=None)


class AgentStep(SQLModel, table=True):
    """A single recorded step in an agent run's plan→act→observe trail."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id", index=True)

    # Monotonic position within the run, for stable ordering in the UI.
    step_index: int = Field(default=0)
    kind: str  # plan | action | result | error

    # Human-readable one-liner; ``detail`` carries the full text / observation.
    title: str
    detail: str | None = Field(default=None)

    # The tool invoked on an ``action`` step (null for plan/result/error).
    tool_name: str | None = Field(default=None)
    status: str = Field(default=STEP_OK)  # ok | failed

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
