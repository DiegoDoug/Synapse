"""Synchronization request/response schemas."""

from datetime import datetime

from pydantic import BaseModel


class SyncResult(BaseModel):
    """Outcome of synchronizing a single resource for one account."""

    account_id: int
    resource: str  # "gmail" | "calendar"
    created: int = 0
    updated: int = 0
    total: int = 0
    status: str = "ok"  # ok | error
    error: str | None = None


class SyncStatusRead(BaseModel):
    """Current sync checkpoint for one account resource."""

    account_id: int
    resource: str
    status: str
    last_synced_at: datetime | None = None
    error: str | None = None
