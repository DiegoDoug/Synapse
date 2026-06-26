"""Stage 3 (Major Feature 2) tests — Telegram delivery, scheduler, commands."""

from datetime import UTC, datetime, timedelta

import pytest
from backend.config import Settings
from backend.main import app
from backend.models.account import Account
from backend.models.calendar_event import CalendarEvent
from backend.models.email_message import EmailMessage
from backend.models.user import User
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.scheduler import create_scheduler
from backend.schemas.notification import NotificationCreate
from backend.services.notification_service import NotificationService
from backend.services.telegram_service import TelegramService
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


class _FakeTelegram:
    """Captures outbound messages; serves canned inbound updates."""

    def __init__(self, updates: list[dict] | None = None) -> None:
        self.sent: list[tuple[str, str]] = []
        self._updates = updates or []

    def send_message(self, chat_id: str, text: str) -> dict:
        self.sent.append((chat_id, text))
        return {"message_id": len(self.sent)}

    def get_updates(self, offset=None, *, timeout: int = 0) -> list[dict]:
        # Return everything at/after offset, mimicking Telegram confirmation.
        if offset is None:
            return list(self._updates)
        return [u for u in self._updates if u["update_id"] >= offset]


def _service(session: Session, telegram=None, chat_id=None) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        AccountRepository(session),
        EmailRepository(session),
        CalendarRepository(session),
        telegram=telegram,
        default_chat_id=chat_id,
    )


def _make_account(session: Session) -> Account:
    return AccountRepository(session).add(
        Account(
            user_id=1,
            provider="google",
            email="owner@localhost",
            access_token="access-token",
        )
    )


# --- API wiring --------------------------------------------------------------


def test_delivery_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/notifications/telegram" in paths
    assert "/api/v1/notifications/deliver" in paths
    assert "/api/v1/notifications/{notification_id}/send" in paths


# --- Delivery ----------------------------------------------------------------


def test_send_marks_delivered(session):
    tg = _FakeTelegram()
    service = _service(session, telegram=tg, chat_id="123")
    n = service.create(1, NotificationCreate(title="Ping"))

    result = service.send(1, n.id)
    assert result is not None and result.configured and result.delivered == 1
    assert len(tg.sent) == 1
    assert tg.sent[0][0] == "123"
    # Re-reading shows the delivered stamp.
    assert service.list(1)[0].is_delivered is True


def test_send_skips_when_unconfigured(session):
    service = _service(session)  # no telegram
    n = service.create(1, NotificationCreate(title="Ping"))
    result = service.send(1, n.id)
    assert result is not None and result.configured is False and result.delivered == 0


def test_send_unknown_returns_none(session):
    service = _service(session, telegram=_FakeTelegram(), chat_id="1")
    assert service.send(1, 999) is None
    assert service.send(2, 1) is None  # wrong user


def test_deliver_pending_only_sends_undelivered(session):
    tg = _FakeTelegram()
    service = _service(session, telegram=tg, chat_id="1")
    a = service.create(1, NotificationCreate(title="A"))
    service.create(1, NotificationCreate(title="B"))
    service.send(1, a.id)  # deliver A first

    result = service.deliver_pending(1)
    assert result.delivered == 1  # only B remained
    assert len(tg.sent) == 2  # A then B


def test_daily_summary_persists_and_is_idempotent(session):
    account = _make_account(session)
    now = datetime.now(UTC)
    EmailRepository(session).upsert(
        EmailMessage(account_id=account.id, external_id="m1", is_read=False)
    )
    CalendarRepository(session).upsert(
        CalendarEvent(
            account_id=account.id,
            external_id="e1",
            summary="Soon",
            start=now + timedelta(hours=3),
        )
    )
    tg = _FakeTelegram()
    service = _service(session, telegram=tg, chat_id="1")

    first = service.daily_summary(1)
    assert first.delivered == 1
    assert len(tg.sent) == 1
    assert "unread email" in tg.sent[0][1]

    # A summary notification is persisted exactly once per day.
    summaries = [n for n in service.list(1) if n.category == "summary"]
    assert len(summaries) == 1

    second = service.daily_summary(1)
    assert second.delivered == 0  # already delivered today
    assert len(tg.sent) == 1


# --- Inbound commands --------------------------------------------------------


def _settings(**overrides) -> Settings:
    base = {
        "telegram_bot_token": "test-token",
        "telegram_default_chat_id": "555",
        "scheduler_enabled": True,
    }
    base.update(overrides)
    return Settings(**base)


def test_telegram_service_routes_commands(session):
    # Seed an unread notification so /unread has something to report.
    _service(session).create(1, NotificationCreate(title="A"))
    # Owner user must exist for data-backed commands.
    session.add(User(id=1, email="owner@localhost"))
    session.commit()

    updates = [
        {"update_id": 10, "message": {"text": "/help", "chat": {"id": 555}}},
        {"update_id": 11, "message": {"text": "/unread", "chat": {"id": 555}}},
        {"update_id": 12, "message": {"text": "hi there", "chat": {"id": 555}}},
        {"update_id": 13, "message": {"text": "/bogus", "chat": {"id": 555}}},
    ]
    tg = _FakeTelegram(updates)
    service = TelegramService(tg, lambda: _NoCloseSession(session), _settings())
    handled = service.poll()

    assert handled == 3  # help, unread, bogus (the plain text is ignored)
    replies = [text for _, text in tg.sent]
    assert any("commands" in r for r in replies)  # /help
    assert any("unread" in r for r in replies)  # /unread
    assert any("Unknown command" in r for r in replies)  # /bogus

    # Second poll: offset advanced past all updates → nothing new.
    assert service.poll() == 0


class _NoCloseSession:
    """Wrap a shared test session so ``with factory()`` doesn't close it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc) -> None:
        return None


# --- Scheduler wiring --------------------------------------------------------


def test_scheduler_disabled_returns_none():
    assert create_scheduler(_settings(scheduler_enabled=False)) is None


def test_scheduler_registers_jobs_with_telegram():
    # Built but not started, so there are no threads to tear down.
    scheduler = create_scheduler(_settings())
    ids = {job.id for job in scheduler.get_jobs()}
    assert ids == {
        "notification-poll",
        "daily-summary",
        "telegram-commands",
        "workflow-events",
    }


def test_scheduler_without_telegram_skips_command_job():
    scheduler = create_scheduler(_settings(telegram_bot_token=""))
    ids = {job.id for job in scheduler.get_jobs()}
    assert ids == {"notification-poll", "daily-summary", "workflow-events"}
