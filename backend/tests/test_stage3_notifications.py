"""Stage 3 (Major Feature 1) tests — in-app notification center + composition."""

from datetime import UTC, datetime, timedelta

import pytest
from backend.main import app
from backend.models.account import Account
from backend.models.calendar_event import CalendarEvent
from backend.models.email_message import EmailMessage
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.schemas.notification import NotificationCreate
from backend.services.notification_service import NotificationService
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _service(session: Session) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        AccountRepository(session),
        EmailRepository(session),
        CalendarRepository(session),
    )


def _make_account(session: Session, user_id: int = 1) -> Account:
    return AccountRepository(session).add(
        Account(
            user_id=user_id,
            provider="google",
            email="owner@localhost",
            access_token="access-token",
        )
    )


# --- API wiring --------------------------------------------------------------


def test_notification_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/notifications" in paths
    assert "/api/v1/notifications/counts" in paths
    assert "/api/v1/notifications/compose" in paths
    assert "/api/v1/notifications/read-all" in paths
    assert "/api/v1/notifications/{notification_id}/read" in paths


# --- Center: create / list / counts / mark read ------------------------------


def test_create_list_and_counts(session):
    service = _service(session)

    created = service.create(1, NotificationCreate(title="Hello", body="World"))
    assert created.id is not None
    assert created.category == "manual"
    assert created.is_read is False

    listed = service.list(1)
    assert len(listed) == 1
    assert listed[0].title == "Hello"

    counts = service.counts(1)
    assert counts.unread == 1
    assert counts.total == 1


def test_mark_read_and_mark_all_read(session):
    service = _service(session)
    a = service.create(1, NotificationCreate(title="A"))
    service.create(1, NotificationCreate(title="B"))

    marked = service.mark_read(1, a.id)
    assert marked is not None and marked.is_read is True and marked.read_at is not None
    assert service.counts(1).unread == 1

    changed = service.mark_all_read(1)
    assert changed == 1  # only the remaining unread one
    assert service.counts(1).unread == 0


def test_mark_read_rejects_other_users_notification(session):
    service = _service(session)
    mine = service.create(1, NotificationCreate(title="Mine"))
    # A different user cannot mark it read.
    assert service.mark_read(2, mine.id) is None
    # Unknown id is also a miss.
    assert service.mark_read(1, 999) is None


# --- Composition from synced data --------------------------------------------


def test_compose_builds_reminders_and_alerts_and_dedupes(session):
    account = _make_account(session)
    now = datetime.now(UTC)

    # An upcoming event within the 24h window → reminder.
    CalendarRepository(session).upsert(
        CalendarEvent(
            account_id=account.id,
            external_id="evt-1",
            summary="Standup",
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=2, minutes=30),
        )
    )
    # A far-future event → no reminder.
    CalendarRepository(session).upsert(
        CalendarEvent(
            account_id=account.id,
            external_id="evt-far",
            summary="Later",
            start=now + timedelta(days=10),
        )
    )
    # An unread email → alert.
    EmailRepository(session).upsert(
        EmailMessage(
            account_id=account.id,
            external_id="msg-1",
            subject="Welcome",
            sender="alice@example.com",
            is_read=False,
        )
    )
    # A read email → no alert.
    EmailRepository(session).upsert(
        EmailMessage(
            account_id=account.id,
            external_id="msg-read",
            subject="Old",
            sender="bob@example.com",
            is_read=True,
        )
    )

    service = _service(session)
    first = service.compose(1)
    assert first.created == 2
    categories = {n.category for n in first.notifications}
    assert categories == {"reminder", "alert"}

    # Re-running composition is idempotent (source_key dedupe).
    second = service.compose(1)
    assert second.created == 0
    assert service.counts(1).total == 2


def test_compose_handles_all_day_naive_start(session):
    account = _make_account(session)
    now = datetime.now(UTC)
    # All-day events store a naive (date-only) start; composition must not crash
    # comparing it against an aware "now".
    CalendarRepository(session).upsert(
        CalendarEvent(
            account_id=account.id,
            external_id="evt-allday",
            summary="Holiday",
            all_day=True,
            start=(now + timedelta(hours=5)).replace(tzinfo=None),
        )
    )
    result = _service(session).compose(1)
    assert result.created == 1
    assert result.notifications[0].body.startswith("all day")
