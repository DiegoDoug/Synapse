"""Stage 2 integration tests — wiring + Gmail sync mapping (no live APIs)."""

from datetime import UTC, datetime

import pytest
from backend.main import app
from backend.models.account import Account
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.services import calendar_service as calendar_service_module
from backend.services import email_service as email_service_module
from backend.services.calendar_service import CalendarService
from backend.services.email_service import EmailService
from backend.services.sync_service import SyncService
from fastapi.testclient import TestClient
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


# --- API wiring --------------------------------------------------------------


def test_health_ok():
    client = TestClient(app)
    assert client.get("/api/v1/health").json() == {"status": "healthy"}


def test_stage2_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/connections" in paths
    assert "/api/v1/connections/google/authorize" in paths
    assert "/api/v1/accounts/{account_id}/emails" in paths
    assert "/api/v1/accounts/{account_id}/emails/sync" in paths
    assert "/api/v1/accounts/{account_id}/events" in paths
    assert "/api/v1/accounts/{account_id}/events/sync" in paths
    assert "/api/v1/accounts/{account_id}/sync" in paths
    assert "/api/v1/accounts/{account_id}/sync/status" in paths


def test_connections_require_google_config():
    # With no GOOGLE_CLIENT_ID/SECRET configured, the dependency returns 503.
    client = TestClient(app)
    assert client.get("/api/v1/connections").status_code == 503


# --- Gmail sync logic (fakes for the integration layer) ----------------------


class _FakeCredentials:
    def __init__(self):
        self.token = "access-token"
        self.refresh_token = "refresh-token"
        self.expiry = None
        self.expired = False


class _FakeOAuth:
    def credentials_from_tokens(self, *args, **kwargs):
        return _FakeCredentials()

    def refresh(self, credentials):
        return credentials


class _FakeGmail:
    """Stands in for GmailIntegration; canned responses, no HTTP."""

    def __init__(self, credentials):
        pass

    def list_recent_message_ids(self, max_results):
        return ["msg-1"]

    def get_profile(self):
        return {"historyId": "42"}

    def get_message(self, message_id):
        return {
            "id": message_id,
            "threadId": "thread-1",
            "snippet": "hello there",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "owner@localhost"},
                    {"name": "Subject", "value": "Welcome"},
                    {"name": "Date", "value": "Tue, 24 Jun 2026 10:00:00 +0000"},
                ]
            },
        }


def _make_account(session: Session) -> Account:
    return AccountRepository(session).add(
        Account(
            user_id=1,
            provider="google",
            email="owner@localhost",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expiry=datetime.now(UTC),
            scopes="https://www.googleapis.com/auth/gmail.readonly",
        )
    )


def test_initial_sync_maps_and_persists(session, monkeypatch):
    monkeypatch.setattr(email_service_module, "GmailIntegration", _FakeGmail)
    account = _make_account(session)

    service = EmailService(
        AccountRepository(session),
        EmailRepository(session),
        SyncStateRepository(session),
        _FakeOAuth(),
    )

    result = service.sync(account.id)
    assert result.status == "ok"
    assert result.created == 1
    assert result.updated == 0

    messages = service.list_messages(account.id)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.subject == "Welcome"
    assert msg.sender == "alice@example.com"
    assert msg.is_read is False  # UNREAD label present

    # Cursor advanced to the profile historyId.
    state = SyncStateRepository(session).get(account.id, "gmail")
    assert state is not None and state.cursor == "42"
    assert state.status == "idle"


def test_second_sync_updates_existing(session, monkeypatch):
    monkeypatch.setattr(email_service_module, "GmailIntegration", _FakeGmail)
    account = _make_account(session)
    service = EmailService(
        AccountRepository(session),
        EmailRepository(session),
        SyncStateRepository(session),
        _FakeOAuth(),
    )

    first = service.sync(account.id)
    assert first.created == 1

    # Force the history path to return the same message id as an update.
    monkeypatch.setattr(
        _FakeGmail, "list_history", lambda self, cursor: (["msg-1"], "43"), raising=False
    )
    second = service.sync(account.id)
    assert second.created == 0
    assert second.updated == 1
    assert SyncStateRepository(session).get(account.id, "gmail").cursor == "43"


# --- Calendar sync logic -----------------------------------------------------


class _FakeCalendar:
    """Stands in for GoogleCalendarIntegration; canned responses, no HTTP."""

    def __init__(self, credentials):
        pass

    def list_events(self, calendar_id="primary", sync_token=None, max_results=250):
        events = [
            {
                "id": "evt-1",
                "summary": "Standup",
                "location": "Room 1",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-25T09:00:00+00:00"},
                "end": {"dateTime": "2026-06-25T09:30:00+00:00"},
            },
            {
                "id": "evt-2",
                "summary": "Holiday",
                "status": "confirmed",
                "start": {"date": "2026-07-04"},
                "end": {"date": "2026-07-05"},
            },
        ]
        return events, "sync-token-1"


def _calendar_service(session: Session) -> CalendarService:
    return CalendarService(
        AccountRepository(session),
        CalendarRepository(session),
        SyncStateRepository(session),
        _FakeOAuth(),
    )


def test_calendar_sync_maps_timed_and_all_day(session, monkeypatch):
    monkeypatch.setattr(
        calendar_service_module, "GoogleCalendarIntegration", _FakeCalendar
    )
    account = _make_account(session)
    service = _calendar_service(session)

    result = service.sync(account.id)
    assert result.status == "ok"
    assert result.created == 2

    events = {e.external_id: e for e in service.list_events(account.id)}
    assert events["evt-1"].all_day is False
    assert events["evt-2"].all_day is True
    assert events["evt-2"].summary == "Holiday"

    state = SyncStateRepository(session).get(account.id, "calendar")
    assert state is not None and state.cursor == "sync-token-1"


def test_sync_service_runs_both_resources(session, monkeypatch):
    monkeypatch.setattr(email_service_module, "GmailIntegration", _FakeGmail)
    monkeypatch.setattr(
        calendar_service_module, "GoogleCalendarIntegration", _FakeCalendar
    )
    account = _make_account(session)

    email_service = EmailService(
        AccountRepository(session),
        EmailRepository(session),
        SyncStateRepository(session),
        _FakeOAuth(),
    )
    sync_service = SyncService(
        email_service, _calendar_service(session), SyncStateRepository(session)
    )

    results = sync_service.sync_account(account.id)
    assert {r.resource for r in results} == {"gmail", "calendar"}
    assert all(r.status == "ok" for r in results)

    statuses = {s.resource: s for s in sync_service.get_status(account.id)}
    assert set(statuses) == {"gmail", "calendar"}
    assert all(s.status == "idle" for s in statuses.values())
