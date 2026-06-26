"""AgentService — the API-facing facade over the agent layer.

Lists the available agents, starts a run (executing it synchronously through the
``AgentRunner`` against the user-scoped ``ToolRegistry``), and reads a run's
status/steps and recent history. All reads are scoped to the owning user.

It composes existing pieces — the ``AgentRegistry`` (what can run), the
``AgentRunner`` (how a run is recorded), and a ``ToolRegistry`` already wired
with the confirmation flow and knowledge search — rather than introducing any
new side-effect path.
"""

from __future__ import annotations

from typing import Any

from backend.agents.registry import AgentRegistry
from backend.agents.runner import AgentRunner
from backend.models.agent_run import AgentRun, AgentStep
from backend.repositories.agent_run_repository import AgentRunRepository
from backend.schemas.agent import (
    AgentInfo,
    AgentParam,
    AgentRunRead,
    AgentRunSummary,
    AgentStepRead,
)
from backend.services.tools.registry import ToolRegistry


class AgentService:
    """List agents, start runs, and read run status/history for a user."""

    def __init__(
        self,
        agents: AgentRegistry,
        runner: AgentRunner,
        runs: AgentRunRepository,
        tools: ToolRegistry,
    ) -> None:
        self._agents = agents
        self._runner = runner
        self._runs = runs
        self._tools = tools

    # --- Catalogue ---------------------------------------------------------

    def list_agents(self) -> list[AgentInfo]:
        return [
            AgentInfo(
                key=agent.key,
                name=agent.name,
                description=agent.description,
                parameters=[AgentParam(**p) for p in agent.parameters],
            )
            for agent in self._agents.list()
        ]

    # --- Runs --------------------------------------------------------------

    def start(
        self, user_id: int, agent_key: str, params: dict[str, Any]
    ) -> AgentRunRead | None:
        """Run an agent and return the completed run, or None if unknown."""
        agent = self._agents.get(agent_key)
        if agent is None:
            return None
        run = self._runner.run(user_id, agent, self._tools, params)
        return self._run_read(run)

    def get_run(self, user_id: int, run_id: int) -> AgentRunRead | None:
        run = self._owned(user_id, run_id)
        return self._run_read(run) if run else None

    def list_runs(
        self, user_id: int, *, limit: int = 50
    ) -> list[AgentRunSummary]:
        return [
            self._run_summary(run)
            for run in self._runs.list_for_user(user_id, limit=limit)
        ]

    # --- Internals ---------------------------------------------------------

    def _owned(self, user_id: int, run_id: int) -> AgentRun | None:
        run = self._runs.get(run_id)
        if run is None or run.user_id != user_id:
            return None
        return run

    def _run_read(self, run: AgentRun) -> AgentRunRead:
        steps = self._runs.list_steps(run.id)
        return AgentRunRead(
            **self._run_summary(run).model_dump(),
            steps=[self._step_read(s) for s in steps],
        )

    @staticmethod
    def _run_summary(run: AgentRun) -> AgentRunSummary:
        return AgentRunSummary(
            id=run.id,
            agent_key=run.agent_key,
            agent_name=run.agent_name,
            input=run.input,
            status=run.status,
            result=run.result,
            error=run.error,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )

    @staticmethod
    def _step_read(step: AgentStep) -> AgentStepRead:
        return AgentStepRead(
            id=step.id,
            step_index=step.step_index,
            kind=step.kind,
            title=step.title,
            detail=step.detail,
            tool_name=step.tool_name,
            status=step.status,
            created_at=step.created_at,
        )
