"""Calendar request/response schemas (DTOs)."""

from datetime import datetime

from pydantic import BaseModel


class EventSummary(BaseModel):
    """List-view representation of a synced calendar event."""

    id: int
    external_id: str
    summary: str | None = None
    location: str | None = None
    all_day: bool = False
    start: datetime | None = None
    end: datetime | None = None
    status: str | None = None


class EventDetail(EventSummary):
    """Detail-view representation of a synced calendar event."""

    account_id: int
    calendar_id: str | None = None
    description: str | None = None
