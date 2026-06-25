"""ToolRegistry — advertises tools to the provider and executes tool calls.

Holds the available tools plus the per-request ``ToolContext`` they run
against. ``specs()`` is what the provider sees; ``execute()`` dispatches a
model tool call by name and always returns text (errors included) so a single
failing tool never breaks the tool-use loop.
"""

import logging
from typing import Any

from backend.schemas.ai import ToolSpec
from backend.services.tools.base import Tool, ToolContext

logger = logging.getLogger(__name__)


class ToolRegistry:
    """A name→tool map bound to a request's ToolContext."""

    def __init__(self, tools: list[Tool], context: ToolContext) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._context = context

    def __bool__(self) -> bool:
        return bool(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        try:
            return tool.run(arguments, self._context)
        except Exception as exc:  # noqa: BLE001 — never break the loop on a tool
            logger.warning("Tool %s failed: %s", name, exc)
            return f"Tool '{name}' failed: {exc}"
