"""AgentRegistry — the catalogue of available domain agents.

A simple name→agent map so routes can list what can be run and resolve a key to
its agent. Distinct from the ``ToolRegistry`` (which advertises tools to a
provider): this advertises whole agents to the user. ``build_agent_registry``
is the single place new agents are registered.
"""

from __future__ import annotations

from backend.agents.base import Agent
from backend.agents.study_agent import StudyAgent


class AgentRegistry:
    """A key→agent map of the agents the system can run."""

    def __init__(self, agents: list[Agent]) -> None:
        self._agents = {agent.key: agent for agent in agents}

    def list(self) -> list[Agent]:
        return list(self._agents.values())

    def get(self, key: str) -> Agent | None:
        return self._agents.get(key)


def build_agent_registry() -> AgentRegistry:
    """Assemble the registry of all available agents."""
    return AgentRegistry(
        [
            StudyAgent(),
        ]
    )
