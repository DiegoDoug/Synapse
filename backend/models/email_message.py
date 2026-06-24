"""EmailMessage model (SQLModel). Schema only — no business logic.

A locally-stored copy of Gmail message metadata produced by the email sync.
Read-only ingestion in this stage: body content and attachments are out of
scope.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class EmailMessage(SQLModel, table=True):
    """Synced Gmail message metadata."""

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id", index=True)

    external_id: str = Field(index=True)  # Gmail message id
    thread_id: str | None = Field(default=None, index=True)

    sender: str | None = Field(default=None)
    recipient: str | None = Field(default=None)
    subject: str | None = Field(default=None)
    snippet: str | None = Field(default=None)
    labels: str | None = Field(default=None)  # space-separated Gmail label ids

    is_read: bool = Field(default=False)
    received_at: datetime | None = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
