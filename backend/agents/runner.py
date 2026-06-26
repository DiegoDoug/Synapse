"""AgentRunner — executes an agent and records its run to the audit trail.

The single place an agent run is driven: it opens an ``AgentRun``, records the
plan, runs the agent's plan→act→observe loop (each tool call recorded as it
happens), then records the final result and marks the run completed. A failure
is caught and recorded as an ``error`` step with the run marked failed, so a run
never crashes the caller and partial progress is preserved for inspection.

Execution is synchronous (no background workers — that is Stage 7): the run is
fully recorded by the time ``run`` returns. The runner only talks to the
``AgentRunRepository`` and the agent; it never touches integrations directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.agents.base import Agent, AgentContext
from backend.models.agent_run import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    STEP_ERROR,
    STEP_PLAN,
    STEP_RESULT,
    AgentRun,
    AgentStep,
)
from backend.repositories.agent_run_repository import AgentRunRepository
from backend.services.tools.registry import ToolRegistry


class AgentRunner:
    """Drive an agent end to end, persisting every step of the run."""

    def __init__(self, runs: AgentRunRepository) -> None:
        self._runs = runs

    def run(
        self,
        user_id: int,
        agent: Agent,
        registry: ToolRegistry,
        params: dict[str, Any],
    ) -> AgentRun:
        """Execute ``agent`` for ``user_id`` and return the recorded run."""
        run = self._runs.add_run(
            AgentRun(
                user_id=user_id,
                agent_key=agent.key,
                agent_name=agent.name,
                input=params or {},
                status=RUN_RUNNING,
            )
        )
        recorder = _Recorder(self._runs, run.id)
        ctx = AgentContext(user_id, params, registry, recorder)

        try:
            recorder.record(STEP_PLAN, agent.plan(ctx))
            result = agent.run(ctx)
            recorder.record(STEP_RESULT, "Result", detail=result)
            run.status = RUN_COMPLETED
            run.result = result
        except Exception as exc:  # noqa: BLE001 — a run must never crash the caller
            reason = f"{type(exc).__name__}: {exc}"
            recorder.record(STEP_ERROR, "Run failed", detail=reason, status="failed")
            run.status = RUN_FAILED
            run.error = reason

        run.finished_at = datetime.now(UTC)
        return self._runs.update_run(run)


class _Recorder:
    """Append-only step writer bound to one run; assigns step ordering."""

    def __init__(self, runs: AgentRunRepository, run_id: int) -> None:
        self._runs = runs
        self._run_id = run_id
        self._index = 0

    def record(
        self,
        kind: str,
        title: str,
        *,
        detail: str | None = None,
        tool_name: str | None = None,
        status: str = "ok",
    ) -> None:
        self._runs.add_step(
            AgentStep(
                run_id=self._run_id,
                step_index=self._index,
                kind=kind,
                title=title,
                detail=detail,
                tool_name=tool_name,
                status=status,
            )
        )
        self._index += 1
