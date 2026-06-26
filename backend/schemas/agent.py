"""Agent request/response schemas (DTOs). Mirrors backend/models/agent_run.py.

Typed shapes for the agents API: the catalogue of runnable agents, the body to
start a run, and read views of a run with its plan→act→observe steps. No
business logic.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentParam(BaseModel):
    """One input parameter an agent accepts, for the trigger form."""

    name: str
    type: str = "string"
    required: bool = False
    description: str | None = None


class AgentInfo(BaseModel):
    """Catalogue entry for a runnable agent."""

    key: str
    name: str
    description: str
    parameters: list[AgentParam] = Field(default_factory=list)


class StartRunRequest(BaseModel):
    """Body for POST /agents/{key}/runs — the agent's input parameters."""

    params: dict[str, Any] = Field(default_factory=dict)


class AgentStepRead(BaseModel):
    """Read-view of a single recorded step in a run's trail."""

    id: int
    step_index: int
    kind: str  # plan | action | result | error
    title: str
    detail: str | None = None
    tool_name: str | None = None
    status: str
    created_at: datetime


class AgentRunSummary(BaseModel):
    """Read-view of a run without its steps (for the history list)."""

    id: int
    agent_key: str
    agent_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    status: str  # running | completed | failed
    result: str | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class AgentRunRead(AgentRunSummary):
    """A run together with its ordered plan→act→observe steps."""

    steps: list[AgentStepRead] = Field(default_factory=list)
