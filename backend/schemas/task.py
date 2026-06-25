"""Task request/response schemas (DTOs). Mirrors backend/models/task.py.

No business logic — just the typed shapes for the tasks API and for read views
returned by ``TaskService``.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Body for POST /tasks (and the ``create_task`` tool payload)."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: str = Field(default="normal")  # low | normal | high
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    """Body for PATCH /tasks/{id} (and the ``update_task`` tool payload).

    Every field is optional; only those supplied are changed.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = None  # todo | done
    priority: str | None = None  # low | normal | high
    due_at: datetime | None = None


class TaskRead(BaseModel):
    """Read-view of a single task."""

    id: int
    user_id: int
    title: str
    description: str | None = None
    status: str
    priority: str
    due_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
