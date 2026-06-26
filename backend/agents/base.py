"""Agent contract and execution context.

An ``Agent`` is a small, declarative orchestrator: it composes the existing
read/write tools (carried by a ``ToolRegistry``) into a multi-step workflow. It
never touches integrations or repositories directly — it acts only through tools,
which route to services, satisfying the Agent → Service → Integration contract.

Agents drive the loop through ``AgentContext``:

- ``ctx.param(...)`` reads a run input parameter.
- ``ctx.act(tool, args, title=...)`` invokes a tool, records the call and the
  result it observed as one ``action`` step, and returns the observation text.

The base ``execute`` wraps an agent's ``run`` with plan/result/error recording
and never raises out of a run — a failure becomes a recorded ``error`` step and
a ``failed`` run, so an unavailable service degrades gracefully (see the
graceful-degradation contract in CURRENT_SPRINT.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from backend.services.tools.registry import ToolRegistry

# Tool result sentinels (from ToolRegistry.execute) that mark a failed action,
# so an action step can be flagged ``failed`` without raising.
_ERROR_PREFIXES = ("Unknown tool:", "Tool '")


class StepRecorder(Protocol):
    """Sink the context writes plan/act/observe steps to (the runner)."""

    def record(
        self,
        kind: str,
        title: str,
        *,
        detail: str | None = None,
        tool_name: str | None = None,
        status: str = "ok",
    ) -> None: ...


class AgentContext:
    """Per-run handle an agent uses to read inputs and drive tools."""

    def __init__(
        self,
        user_id: int,
        params: dict[str, Any],
        registry: ToolRegistry,
        recorder: StepRecorder,
    ) -> None:
        self.user_id = user_id
        self._params = params or {}
        self._registry = registry
        self._recorder = recorder

    def param(self, name: str, default: Any = None) -> Any:
        """Return a run input parameter, or ``default`` when absent."""
        value = self._params.get(name, default)
        return value if value is not None else default

    def act(
        self, tool_name: str, arguments: dict[str, Any], *, title: str
    ) -> str:
        """Invoke a tool, record the observed result as a step, return it.

        Tool failures never raise: ``ToolRegistry.execute`` returns an error
        string, which is recorded as a ``failed`` action step and handed back so
        the agent can decide how to proceed.
        """
        result = self._registry.execute(tool_name, arguments)
        status = "failed" if self._looks_like_error(result) else "ok"
        self._recorder.record(
            "action",
            title,
            detail=result,
            tool_name=tool_name,
            status=status,
        )
        return result

    @staticmethod
    def _looks_like_error(result: str) -> bool:
        return result.startswith(_ERROR_PREFIXES)


class Agent(ABC):
    """A domain agent: a named, multi-step workflow over the tool layer."""

    # Stable identifier used in URLs and persisted on the run.
    key: str
    # Display name and one-line description for the agents UI.
    name: str
    description: str
    # Optional input parameters the agent accepts (advertised to the UI).
    parameters: list[dict[str, Any]] = []

    def plan(self, ctx: AgentContext) -> str:
        """A short description of the approach, recorded before acting.

        Override to tailor the plan to the run's inputs; the default is the
        agent's static description.
        """
        return self.description

    @abstractmethod
    def run(self, ctx: AgentContext) -> str:
        """Execute the workflow and return the final result text.

        Implementations compose ``ctx.act(...)`` calls. Raising is allowed; the
        runner records it as an ``error`` step and marks the run failed.
        """
        raise NotImplementedError
