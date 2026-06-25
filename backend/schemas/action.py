"""Pending-action schemas (DTOs). Mirrors backend/models/pending_action.py.

``ProposedAction`` is the in-process descriptor a write tool hands to the
``ConfirmationService`` (tool name + change kind + payload). ``PendingActionRead``
is the API/SSE read view of a stored proposal. No business logic here.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProposedAction(BaseModel):
    """A write a tool wants to perform, before confirmation is decided.

    The ``ConfirmationService`` either runs it immediately (autonomous creates)
    or stores it as a ``PendingAction`` (updates / deletes). External or browser
    writes set ``requires_confirmation=True`` to force approval regardless of
    ``action_type`` — outbound actions are never autonomous.
    """

    tool_name: str
    action_type: str  # create | update | delete
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    # Override the action_type policy: True forces confirmation, None defers.
    requires_confirmation: bool | None = None


class PendingActionRead(BaseModel):
    """Read-view of a proposed action surfaced in the confirmation modal."""

    id: int
    conversation_id: int | None = None
    tool_name: str
    action_type: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    result: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
