"""Conversation model (SQLModel). Schema only — no business logic.

A Conversation groups an ordered series of chat Messages exchanged with the AI
assistant. It belongs to a single user and carries a human-readable title shown
in the assistant's conversation sidebar. Messages reference it by id.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    """A persisted AI chat conversation (a thread of messages)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    title: str = Field(default="New conversation")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    # Bumped whenever a message is appended so the sidebar can sort by recency.
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
