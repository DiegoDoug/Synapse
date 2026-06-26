"""Internal event sources for event-triggered workflows.

An event trigger fires a workflow when *new already-synced data* appears — a new
email, calendar event, or notification. This module computes a monotonic
high-water mark (the highest source row id) for each event type, read-only and
through repositories. The ``WorkflowService`` compares the mark to a workflow's
stored cursor: a higher mark means new data arrived since the last check.

Triggers never call integrations directly — they observe what Stage 2/3 sync has
already written, satisfying the Automation → Service → Integration contract.
"""

from __future__ import annotations

from sqlmodel import Session

from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository

# Event types a workflow can react to.
EVENT_NEW_EMAIL = "new_email"
EVENT_NEW_CALENDAR_EVENT = "new_calendar_event"
EVENT_NEW_NOTIFICATION = "new_notification"

EVENT_TYPES = (
    EVENT_NEW_EMAIL,
    EVENT_NEW_CALENDAR_EVENT,
    EVENT_NEW_NOTIFICATION,
)

# Human labels for the UI catalogue.
EVENT_LABELS: dict[str, str] = {
    EVENT_NEW_EMAIL: "New email synced",
    EVENT_NEW_CALENDAR_EVENT: "New calendar event synced",
    EVENT_NEW_NOTIFICATION: "New notification raised",
}


def current_mark(session: Session, user_id: int, event_type: str) -> int:
    """Highest source row id for ``event_type`` (0 when there's nothing yet).

    Email/calendar rows are account-scoped, so they are resolved through the
    user's connected accounts; notifications are already user-scoped.
    """
    if event_type == EVENT_NEW_NOTIFICATION:
        return NotificationRepository(session).max_id_for_user(user_id)

    account_ids = [a.id for a in AccountRepository(session).list_for_user(user_id)]
    if event_type == EVENT_NEW_EMAIL:
        return EmailRepository(session).max_id_for_accounts(account_ids)
    if event_type == EVENT_NEW_CALENDAR_EVENT:
        return CalendarRepository(session).max_id_for_accounts(account_ids)
    return 0
