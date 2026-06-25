"""SystemPrompt model (SQLModel). Schema only — no business logic.

A SystemPrompt is a named, reusable system instruction the user can select to
steer the assistant (e.g. "Concise", "Study tutor"). Named ``SystemPrompt``
rather than ``Prompt`` to avoid ambiguity with future prompt templates, tool
prompts, or agent prompts. No template variables or tool wiring in this stage.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SystemPrompt(SQLModel, table=True):
    """A named, selectable system prompt for the assistant."""

    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(index=True, unique=True)
    description: str | None = Field(default=None)
    system_prompt: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
