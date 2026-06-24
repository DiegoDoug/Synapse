"""SyncState model (SQLModel). Schema only — no business logic.

Tracks incremental synchronization for a single (account, resource) pair so a
sync can resume from where it left off. The cursor stores the provider-specific
checkpoint (e.g. a Gmail historyId or a Calendar syncToken).
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SyncState(SQLModel, table=True):
    """Synchronization checkpoint for one account resource."""

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id", index=True)

    resource: str = Field(index=True)  # "gmail" | "calendar"
    cursor: str | None = Field(default=None)  # historyId / syncToken / pageToken
    status: str = Field(default="idle")  # idle | syncing | error
    error: str | None = Field(default=None)

    last_synced_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
