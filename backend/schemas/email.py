"""Email request/response schemas (DTOs)."""

from datetime import datetime

from pydantic import BaseModel


class EmailSummary(BaseModel):
    """List-view representation of a synced email."""

    id: int
    external_id: str
    thread_id: str | None = None
    sender: str | None = None
    subject: str | None = None
    snippet: str | None = None
    is_read: bool = False
    received_at: datetime | None = None


class EmailDetail(EmailSummary):
    """Detail-view representation of a synced email."""

    account_id: int
    recipient: str | None = None
    labels: list[str] = []
