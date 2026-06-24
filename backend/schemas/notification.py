"""Notification request/response schemas (DTOs)."""

from datetime import datetime

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    """Read-view representation of a notification."""

    id: int
    category: str
    priority: str
    title: str
    body: str | None = None
    source: str | None = None
    is_read: bool = False
    read_at: datetime | None = None
    created_at: datetime


class NotificationCreate(BaseModel):
    """Payload for a manually created in-app notification."""

    title: str = Field(min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=2000)
    category: str = "manual"
    priority: str = "normal"


class NotificationCounts(BaseModel):
    """Aggregate counts for the notification center badge."""

    unread: int
    total: int


class ComposeResult(BaseModel):
    """Outcome of composing notifications from synced data."""

    created: int
    notifications: list[NotificationRead] = []


class MarkAllReadResult(BaseModel):
    """Number of notifications transitioned to read."""

    updated: int
