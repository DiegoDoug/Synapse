"""PendingAction model (SQLModel). Schema only — no business logic.

A PendingAction records a write the assistant has *proposed* but not yet
executed. Creates are autonomous and never produce a pending row; updates and
deletes (and, from Stage 4.5 Major Feature 2, browser writes) are stored here
as ``pending`` until the user approves or rejects them. The ``ConfirmationService``
owns this lifecycle and the ``ToolExecutor`` runs the action on approval.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

# Status values for a pending action's lifecycle.
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXECUTED = "executed"
STATUS_FAILED = "failed"


class PendingAction(SQLModel, table=True):
    """A proposed write awaiting (or past) user confirmation."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    # Thread the proposal originated from, so the chat UI can surface it.
    conversation_id: int | None = Field(default=None, index=True)

    # The write tool that proposed this action and the kind of change it makes.
    tool_name: str
    action_type: str  # create | update | delete

    # Human-readable one-liner shown in the confirmation modal.
    summary: str
    # Tool arguments to replay on approval (provider-neutral JSON).
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )

    status: str = Field(default=STATUS_PENDING, index=True)
    # Result text from execution (success detail or failure reason).
    result: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    resolved_at: datetime | None = Field(default=None)
