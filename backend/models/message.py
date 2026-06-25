"""Message model (SQLModel). Schema only — no business logic.

A Message is a single turn in a Conversation: a user prompt, an assistant
reply, or a system instruction. ``provider`` records which LLM produced an
assistant message so the UI can show a provider indicator. No embeddings or
memory are stored here (those belong to Stage 5).
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """A single message within a conversation."""

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)

    # role — "user" | "assistant" | "system"
    role: str = Field(index=True)
    content: str

    # The provider/model that produced this message (assistant turns only).
    provider: str | None = Field(default=None)
    model: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
