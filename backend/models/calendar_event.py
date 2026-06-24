"""CalendarEvent model (SQLModel). Schema only — no business logic.

A locally-stored copy of a Google Calendar event produced by the calendar sync.
Read-only ingestion in this stage.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class CalendarEvent(SQLModel, table=True):
    """Synced Google Calendar event."""

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id", index=True)

    external_id: str = Field(index=True)  # Calendar event id
    calendar_id: str | None = Field(default=None, index=True)

    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    location: str | None = Field(default=None)
    status: str | None = Field(default=None)  # confirmed | tentative | cancelled

    all_day: bool = Field(default=False)
    start: datetime | None = Field(default=None, index=True)
    end: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
