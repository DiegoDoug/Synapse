"""Notification service — compose, list, and update in-app notifications.

Business logic for the notification center. It reads already-synced emails and
calendar events (via their repositories) and turns them into timely, deduped
notifications: reminders for upcoming events and alerts for unread mail. It also
exposes the center reads (list, counts) and state changes (mark read).

This stage is in-app only: notifications are persisted and surfaced in the UI.
External delivery (Telegram) and scheduled composition are layered on top later
without changing this service's contract. No AI/analysis is performed here —
composition is rule-based over synced metadata only.
"""

# Deferred annotations: the public ``list`` method shadows the builtin within
# the class body, so keep return-type hints lazy rather than eval them eagerly.
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.integrations.telegram.bot import TelegramIntegration
from backend.models.calendar_event import CalendarEvent
from backend.models.email_message import EmailMessage
from backend.models.notification import Notification
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.schemas.notification import (
    ComposeResult,
    DeliveryResult,
    NotificationCounts,
    NotificationCreate,
    NotificationRead,
    TelegramStatus,
)
from backend.services.interfaces import NotificationServiceInterface

# How far ahead an event must start to earn a reminder, and the "starting soon"
# threshold that bumps a reminder to high priority.
_REMINDER_WINDOW = timedelta(hours=24)
_SOON_THRESHOLD = timedelta(hours=1)
# Cap email alerts per composition run so a large unread backlog can't flood
# the center on first sync.
_EMAIL_ALERT_LIMIT = 10


class NotificationService(NotificationServiceInterface):
    """Compose notifications from synced data and run the notification center."""

    def __init__(
        self,
        notifications: NotificationRepository,
        accounts: AccountRepository,
        emails: EmailRepository,
        events: CalendarRepository,
        *,
        telegram: TelegramIntegration | None = None,
        default_chat_id: str | None = None,
    ) -> None:
        self._notifications = notifications
        self._accounts = accounts
        self._emails = emails
        self._events = events
        self._telegram = telegram
        self._default_chat_id = default_chat_id or None

    # --- Reads -------------------------------------------------------------

    def list(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[NotificationRead]:
        rows = self._notifications.list_for_user(
            user_id, limit=limit, offset=offset, unread_only=unread_only
        )
        return [self._to_read(row) for row in rows]

    def counts(self, user_id: int) -> NotificationCounts:
        return NotificationCounts(
            unread=self._notifications.count(user_id, unread_only=True),
            total=self._notifications.count(user_id),
        )

    # --- Writes ------------------------------------------------------------

    def create(self, user_id: int, data: NotificationCreate) -> NotificationRead:
        notification = Notification(
            user_id=user_id,
            category=data.category,
            priority=data.priority,
            title=data.title,
            body=data.body,
            source="system",
        )
        return self._to_read(self._notifications.add(notification))

    def mark_read(self, user_id: int, notification_id: int) -> NotificationRead | None:
        row = self._notifications.get(notification_id)
        if row is None or row.user_id != user_id:
            return None
        if not row.is_read:
            row.is_read = True
            row.read_at = datetime.now(UTC)
            self._notifications.update(row)
        return self._to_read(row)

    def mark_all_read(self, user_id: int) -> int:
        return self._notifications.mark_all_read(user_id)

    # --- Delivery (Telegram) ----------------------------------------------

    def telegram_status(self) -> TelegramStatus:
        return TelegramStatus(
            configured=self._telegram is not None,
            chat_configured=bool(self._default_chat_id),
        )

    def send(self, user_id: int, notification_id: int) -> DeliveryResult | None:
        row = self._notifications.get(notification_id)
        if row is None or row.user_id != user_id:
            return None
        if not self._can_deliver():
            return DeliveryResult(configured=False, skipped=1)
        self._dispatch(self._format(row))
        self._mark_delivered(row)
        return DeliveryResult(configured=True, delivered=1)

    def deliver_pending(self, user_id: int) -> DeliveryResult:
        if not self._can_deliver():
            pending = self._notifications.list_undelivered(user_id)
            return DeliveryResult(configured=False, skipped=len(pending))
        delivered = 0
        for row in self._notifications.list_undelivered(user_id):
            self._dispatch(self._format(row))
            self._mark_delivered(row)
            delivered += 1
        return DeliveryResult(configured=True, delivered=delivered)

    def compose_and_deliver(self, user_id: int) -> DeliveryResult:
        self.compose(user_id)
        return self.deliver_pending(user_id)

    def daily_summary(self, user_id: int) -> DeliveryResult:
        """Persist a once-per-day summary notification and deliver it."""
        source_key = f"summary:{datetime.now(UTC).date().isoformat()}"
        existing = self._notifications.get_by_source_key(user_id, source_key)
        text = self.summary_text(user_id)
        if existing is None:
            notification = self._persist(
                user_id,
                category="summary",
                priority="normal",
                title="Daily summary",
                body=text,
                source="system",
                source_key=source_key,
            )
            row = self._notifications.get(notification.id)
        else:
            row = existing
        if not self._can_deliver():
            return DeliveryResult(configured=False, skipped=1)
        if row.is_delivered:
            return DeliveryResult(configured=True, delivered=0, skipped=1)
        self._dispatch(f"📊 Daily summary\n{text}")
        self._mark_delivered(row)
        return DeliveryResult(configured=True, delivered=1)

    # --- Composition -------------------------------------------------------

    def compose(self, user_id: int) -> ComposeResult:
        """Build notifications from each connected account's synced data.

        Idempotent: every candidate carries a stable ``source_key`` so repeated
        runs (manual or, later, scheduled) never create duplicates.
        """
        created: list[NotificationRead] = []
        now = datetime.now(UTC)
        for account in self._accounts.list_for_user(user_id):
            created.extend(self._compose_event_reminders(user_id, account.id, now))
            created.extend(self._compose_email_alerts(user_id, account.id))
        return ComposeResult(created=len(created), notifications=created)

    def _compose_event_reminders(
        self, user_id: int, account_id: int, now: datetime
    ) -> list[NotificationRead]:
        created: list[NotificationRead] = []
        for event in self._events.list_for_account(account_id, limit=100):
            start = self._ensure_aware(event.start)
            if start is None or not (now <= start <= now + _REMINDER_WINDOW):
                continue
            source_key = f"event:{event.external_id}"
            if self._notifications.get_by_source_key(user_id, source_key):
                continue
            priority = "high" if start - now <= _SOON_THRESHOLD else "normal"
            created.append(
                self._persist(
                    user_id,
                    category="reminder",
                    priority=priority,
                    title=f"Upcoming: {event.summary or 'Untitled event'}",
                    body=self._event_body(event, start),
                    source="calendar",
                    source_key=source_key,
                )
            )
        return created

    def _compose_email_alerts(
        self, user_id: int, account_id: int
    ) -> list[NotificationRead]:
        created: list[NotificationRead] = []
        unread = self._emails.list_for_account(
            account_id, limit=_EMAIL_ALERT_LIMIT, unread_only=True
        )
        for message in unread:
            source_key = f"email:{message.external_id}"
            if self._notifications.get_by_source_key(user_id, source_key):
                continue
            created.append(
                self._persist(
                    user_id,
                    category="alert",
                    priority="normal",
                    title=f"Unread email: {message.subject or '(no subject)'}",
                    body=self._email_body(message),
                    source="email",
                    source_key=source_key,
                )
            )
        return created

    # --- Internals ---------------------------------------------------------

    def _can_deliver(self) -> bool:
        return self._telegram is not None and self._default_chat_id is not None

    def _dispatch(self, text: str) -> None:
        # Guarded by _can_deliver() at the call sites.
        self._telegram.send_message(self._default_chat_id, text)

    def _mark_delivered(self, row: Notification) -> None:
        row.is_delivered = True
        row.delivered_at = datetime.now(UTC)
        self._notifications.update(row)

    def summary_text(self, user_id: int) -> str:
        """Human-readable one-line summary of synced activity (no side effects)."""
        now = datetime.now(UTC)
        end_of_day = now + timedelta(hours=24)
        unread_email = 0
        upcoming = 0
        for account in self._accounts.list_for_user(user_id):
            unread_email += len(
                self._emails.list_for_account(account.id, limit=200, unread_only=True)
            )
            for event in self._events.list_for_account(account.id, limit=200):
                start = self._ensure_aware(event.start)
                if start is not None and now <= start <= end_of_day:
                    upcoming += 1
        return (
            f"{unread_email} unread email(s), "
            f"{upcoming} event(s) in the next 24h."
        )

    @staticmethod
    def _format(row: Notification) -> str:
        prefix = "🔔"
        if row.source == "calendar":
            prefix = "📅"
        elif row.source == "email":
            prefix = "✉️"
        elif row.priority == "high":
            prefix = "⚠️"
        body = f"\n{row.body}" if row.body else ""
        return f"{prefix} {row.title}{body}"

    def _persist(
        self,
        user_id: int,
        *,
        category: str,
        priority: str,
        title: str,
        body: str | None,
        source: str,
        source_key: str,
    ) -> NotificationRead:
        notification = Notification(
            user_id=user_id,
            category=category,
            priority=priority,
            title=title,
            body=body,
            source=source,
            source_key=source_key,
        )
        return self._to_read(self._notifications.add(notification))

    @staticmethod
    def _event_body(event: CalendarEvent, start: datetime) -> str:
        when = "all day" if event.all_day else start.strftime("%Y-%m-%d %H:%M UTC")
        parts = [when]
        if event.location:
            parts.append(event.location)
        return " · ".join(parts)

    @staticmethod
    def _email_body(message: EmailMessage) -> str | None:
        sender = message.sender or "unknown sender"
        return f"From {sender}"

    @staticmethod
    def _ensure_aware(value: datetime | None) -> datetime | None:
        """Normalize naive timestamps (e.g. all-day events) to UTC for safe
        comparison against an aware ``now``."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @staticmethod
    def _to_read(row: Notification) -> NotificationRead:
        return NotificationRead(
            id=row.id,
            category=row.category,
            priority=row.priority,
            title=row.title,
            body=row.body,
            source=row.source,
            is_read=row.is_read,
            read_at=row.read_at,
            is_delivered=row.is_delivered,
            delivered_at=row.delivered_at,
            created_at=row.created_at,
        )
