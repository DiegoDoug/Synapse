"""Notification model (SQLModel). Schema only — no business logic.

A Notification is an in-app message composed by the NotificationService from
synced data (emails, calendar events) or created manually. It powers the
notification center. External delivery (Telegram) is layered on top in a later
step without changing this schema.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    """A persisted in-app notification."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    # Classification — drives grouping and presentation in the center.
    category: str = Field(default="alert", index=True)  # summary | reminder | alert | manual
    priority: str = Field(default="normal")  # low | normal | high

    title: str
    body: str | None = Field(default=None)

    # Provenance — lets composition dedupe against already-created notifications.
    source: str | None = Field(default=None)  # email | calendar | system
    source_key: str | None = Field(default=None, index=True)  # e.g. "email:<external_id>"

    is_read: bool = Field(default=False, index=True)
    read_at: datetime | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
