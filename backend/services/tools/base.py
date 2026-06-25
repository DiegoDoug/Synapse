"""Tool contract and execution context.

A ``Tool`` is a thin, read-only adapter: it declares a name + JSON-schema and
runs against the repositories (or browser) carried by ``ToolContext``. The
context is built per request so every tool is scoped to the current user and
session. Tools return plain text — what the model reads back.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from backend.integrations.browser.service import BrowserService
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.schemas.ai import ToolSpec


@dataclass
class ToolContext:
    """Per-request dependencies available to every tool. Read-only repos."""

    user_id: int
    accounts: AccountRepository
    emails: EmailRepository
    events: CalendarRepository
    notifications: NotificationRepository
    browser: BrowserService | None = None


class Tool(ABC):
    """A single read-only capability the assistant can call."""

    name: str
    description: str
    parameters: dict[str, Any]

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    @abstractmethod
    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        """Execute the tool and return a text result for the model."""
        raise NotImplementedError
