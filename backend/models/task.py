"""Task model (SQLModel). Schema only — no business logic.

A Task is a lightweight to-do owned by a single user. It is the target of the
Stage 4.5 internal write tools (``create_task`` / ``update_task`` /
``delete_task``) that the assistant proposes and the user confirms. Reads of
tasks remain autonomous; updates and deletes pass through the confirmation flow.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    """A persisted personal task / to-do item."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    title: str
    description: str | None = Field(default=None)

    # Lifecycle — "todo" until completed, then "done".
    status: str = Field(default="todo", index=True)  # todo | done
    priority: str = Field(default="normal")  # low | normal | high

    due_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    # Bumped on every edit so lists can sort by recency.
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
