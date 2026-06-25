"""Read-only AI tools and the registry that exposes them to the AIService.

Tools map a provider-neutral name + JSON-schema to an existing read path
(email/calendar/notification repositories, or the read-only BrowserService).
They never write. The registry advertises tool specs to the provider and
executes the model's tool calls.
"""

from backend.services.tools.base import Tool, ToolContext
from backend.services.tools.registry import ToolRegistry

__all__ = ["Tool", "ToolContext", "ToolRegistry"]
