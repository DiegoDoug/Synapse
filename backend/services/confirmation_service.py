"""ConfirmationService — the pending-action lifecycle.

The seam between the assistant's write tools and execution. Tools hand it a
``ProposedAction``; the service decides whether the change runs now or waits for
the user:

- **create** → autonomous: executed immediately via the ``ToolExecutor``.
- **update / delete** → stored as a ``PendingAction`` (status ``pending``) until
  the user approves (then executed) or rejects it.

It also exposes the approve/reject API the confirmation routes call. Execution
always goes through the ``ToolExecutor`` (services), never integrations directly.
Built per request, so ``created_this_turn`` lets the AIService surface proposals
raised during the current chat turn.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.models.pending_action import (
    STATUS_APPROVED,
    STATUS_EXECUTED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
    PendingAction,
)
from backend.repositories.pending_action_repository import PendingActionRepository
from backend.schemas.action import PendingActionRead, ProposedAction
from backend.services.tool_executor import ToolExecutor

# Action types that may run without asking the user. Per CURRENT_SPRINT.md:
# reads and creates are autonomous; updates and deletes require approval.
_AUTONOMOUS = {"create"}


class ConfirmationService:
    """Decide, store, and resolve assistant-proposed write actions."""

    def __init__(
        self, actions: PendingActionRepository, executor: ToolExecutor
    ) -> None:
        self._actions = actions
        self._executor = executor
        self._conversation_id: int | None = None
        # Proposals raised during the current turn, for SSE/result surfacing.
        self._created: list[PendingAction] = []

    # --- Per-turn binding --------------------------------------------------

    def bind_conversation(self, conversation_id: int | None) -> None:
        """Attach proposals raised this turn to a conversation thread."""
        self._conversation_id = conversation_id

    def created_this_turn(self) -> list[PendingActionRead]:
        """Read views of the pending actions proposed during this turn."""
        return [self._to_read(a) for a in self._created]

    # --- Tool entry point --------------------------------------------------

    @staticmethod
    def requires_confirmation(action_type: str) -> bool:
        return action_type not in _AUTONOMOUS

    def handle(self, user_id: int, action: ProposedAction) -> str:
        """Run an autonomous action now, or propose it for confirmation.

        Returns the text the tool feeds back to the model — the execution
        result for autonomous actions, or a 'pending approval' note otherwise.
        """
        if not self.requires_confirmation(action.action_type):
            result = self._executor.execute(
                user_id, action.tool_name, action.payload
            )
            return result.message

        pending = self._actions.add(
            PendingAction(
                user_id=user_id,
                conversation_id=self._conversation_id,
                tool_name=action.tool_name,
                action_type=action.action_type,
                summary=action.summary,
                payload=action.payload,
                status=STATUS_PENDING,
            )
        )
        self._created.append(pending)
        return (
            f"Proposed action #{pending.id} ({action.summary}). "
            "It is awaiting the user's approval and has not run yet."
        )

    # --- Approve / reject API ----------------------------------------------

    def list(
        self, user_id: int, *, pending_only: bool = False
    ) -> list[PendingActionRead]:
        return [
            self._to_read(a)
            for a in self._actions.list_for_user(
                user_id, pending_only=pending_only
            )
        ]

    def get(self, user_id: int, action_id: int) -> PendingActionRead | None:
        action = self._owned(user_id, action_id)
        return self._to_read(action) if action else None

    def approve(self, user_id: int, action_id: int) -> PendingActionRead | None:
        """Execute a pending action. Returns None if not owned/found.

        A non-pending action is returned unchanged (idempotent). Execution
        failures are recorded as ``failed`` with the reason rather than raised.
        """
        action = self._owned(user_id, action_id)
        if action is None:
            return None
        if action.status != STATUS_PENDING:
            return self._to_read(action)

        action.status = STATUS_APPROVED
        result = self._executor.execute(
            user_id, action.tool_name, action.payload
        )
        action.status = STATUS_EXECUTED if result.ok else STATUS_FAILED
        action.result = result.message
        action.resolved_at = datetime.now(UTC)
        return self._to_read(self._actions.update(action))

    def reject(self, user_id: int, action_id: int) -> PendingActionRead | None:
        """Reject a pending action without running it."""
        action = self._owned(user_id, action_id)
        if action is None:
            return None
        if action.status != STATUS_PENDING:
            return self._to_read(action)
        action.status = STATUS_REJECTED
        action.result = "Rejected by user."
        action.resolved_at = datetime.now(UTC)
        return self._to_read(self._actions.update(action))

    # --- Internals ---------------------------------------------------------

    def _owned(self, user_id: int, action_id: int) -> PendingAction | None:
        row = self._actions.get(action_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    @staticmethod
    def _to_read(row: PendingAction) -> PendingActionRead:
        return PendingActionRead(
            id=row.id,
            conversation_id=row.conversation_id,
            tool_name=row.tool_name,
            action_type=row.action_type,
            summary=row.summary,
            payload=row.payload,
            status=row.status,
            result=row.result,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
        )
