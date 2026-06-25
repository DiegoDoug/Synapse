"""Stage 4.5 (Major Feature 2) tests — external write tools + browser writes.

External and browser writes are always confirmed (outbound actions are never
autonomous) and execute through the service layer. Services and the browser are
faked in-memory so no network, OAuth, or Playwright is exercised: the tests
verify routing (everything proposes a pending action), executor dispatch on
approval, graceful degradation when a capability is unconfigured, and that the
browser read tools degrade without Playwright.
"""

import pytest
from backend.integrations.browser.service import BrowserError
from backend.models.account import Account
from backend.repositories.account_repository import AccountRepository
from backend.repositories.pending_action_repository import PendingActionRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.widget_repository import WidgetRepository
from backend.schemas.action import ProposedAction
from backend.services.confirmation_service import ConfirmationService
from backend.services.task_service import TaskService
from backend.services.tool_executor import ToolExecutor
from backend.services.tools.base import ToolContext
from backend.services.tools.web_tools import (
    ExtractStructuredDataTool,
    ScreenshotTool,
)
from backend.services.tools.write_tools import (
    CreateCalendarEventTool,
    DeleteCalendarEventTool,
    FillFormTool,
    SendEmailTool,
    SendTelegramMessageTool,
)
from backend.services.widget_service import WidgetService
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


# --- Fakes -------------------------------------------------------------------


class FakeEmailService:
    def __init__(self):
        self.sent = []

    def send_email(self, account_id, *, to, subject, body):
        self.sent.append((account_id, to, subject, body))
        return "msg-1"


class FakeCalendarService:
    def __init__(self):
        self.created = []
        self.deleted = []

    def create_event(
        self, account_id, *, summary, start, end=None, description=None, location=None
    ):
        self.created.append((account_id, summary, start))
        return "evt-1"

    def delete_event(self, account_id, external_id):
        self.deleted.append((account_id, external_id))


class FakeMessaging:
    def __init__(self):
        self.sent = []

    def send_telegram_message(self, text, *, chat_id=None):
        self.sent.append((text, chat_id))
        return f"Message sent to chat {chat_id or 'default'}."


class FakeBrowser:
    def __init__(self, *, raises=False):
        self.raises = raises
        self.submitted = []

    def fill_and_submit(self, url, fields, *, submit_selector=None):
        if self.raises:
            raise BrowserError("playwright missing")
        self.submitted.append((url, fields, submit_selector))
        return "Thanks for your submission!"


# --- Builders ----------------------------------------------------------------


def _seed_google_account(session: Session) -> Account:
    return AccountRepository(session).add(
        Account(user_id=1, provider="google", email="me@x", access_token="t")
    )


def _executor(session: Session, **overrides) -> ToolExecutor:
    return ToolExecutor(
        TaskService(TaskRepository(session)),
        WidgetService(WidgetRepository(session)),
        accounts=AccountRepository(session),
        **overrides,
    )


def _confirmations(session: Session, executor: ToolExecutor) -> ConfirmationService:
    return ConfirmationService(PendingActionRepository(session), executor)


def _context(session: Session, confirmations: ConfirmationService, browser=None) -> ToolContext:
    return ToolContext(
        user_id=1,
        accounts=None,
        emails=None,
        events=None,
        notifications=None,
        browser=browser,
        confirmations=confirmations,
    )


# --- Confirmation routing: external tools always propose ---------------------


@pytest.mark.parametrize(
    "tool, args",
    [
        (SendEmailTool(), {"to": "a@b.com", "subject": "Hi", "body": "Yo"}),
        (CreateCalendarEventTool(), {"summary": "Lunch", "start": "2026-07-01"}),
        (DeleteCalendarEventTool(), {"event_id": "evt-1"}),
        (SendTelegramMessageTool(), {"text": "ping"}),
        (FillFormTool(), {"url": "https://x.com", "fields": {"#q": "hi"}}),
    ],
)
def test_external_tools_always_require_confirmation(session, tool, args):
    confirmations = _confirmations(session, _executor(session))
    out = tool.run(args, _context(session, confirmations))
    assert "awaiting" in out.lower()
    pending = confirmations.list(1, pending_only=True)
    assert len(pending) == 1 and pending[0].status == "pending"


# --- Executor dispatch on approval -------------------------------------------


def test_approve_send_email_executes(session):
    _seed_google_account(session)
    email = FakeEmailService()
    executor = _executor(session, email=email)
    confirmations = _confirmations(session, executor)
    SendEmailTool().run(
        {"to": "a@b.com", "subject": "Hi", "body": "Yo"},
        _context(session, confirmations),
    )
    action = confirmations.list(1, pending_only=True)[0]
    result = confirmations.approve(1, action.id)
    assert result.status == "executed"
    assert email.sent and email.sent[0][1] == "a@b.com"


def test_approve_calendar_create_and_delete(session):
    _seed_google_account(session)
    calendar = FakeCalendarService()
    executor = _executor(session, calendar=calendar)
    confirmations = _confirmations(session, executor)

    CreateCalendarEventTool().run(
        {"summary": "Lunch", "start": "2026-07-01"},
        _context(session, confirmations),
    )
    DeleteCalendarEventTool().run(
        {"event_id": "evt-9"}, _context(session, confirmations)
    )
    for action in confirmations.list(1, pending_only=True):
        confirmations.approve(1, action.id)
    assert calendar.created and calendar.created[0][1] == "Lunch"
    assert calendar.deleted and calendar.deleted[0][1] == "evt-9"


def test_approve_telegram_send(session):
    messaging = FakeMessaging()
    executor = _executor(session, messaging=messaging)
    confirmations = _confirmations(session, executor)
    SendTelegramMessageTool().run({"text": "ping"}, _context(session, confirmations))
    action = confirmations.list(1, pending_only=True)[0]
    assert confirmations.approve(1, action.id).status == "executed"
    assert messaging.sent == [("ping", None)]


def test_approve_fill_form(session):
    browser = FakeBrowser()
    executor = _executor(session, browser=browser)
    confirmations = _confirmations(session, executor)
    FillFormTool().run(
        {"url": "https://x.com", "fields": {"#q": "hi"}},
        _context(session, confirmations),
    )
    action = confirmations.list(1, pending_only=True)[0]
    result = confirmations.approve(1, action.id)
    assert result.status == "executed"
    assert browser.submitted and browser.submitted[0][0] == "https://x.com"


# --- Graceful failure paths --------------------------------------------------


def test_unconfigured_email_fails_cleanly(session):
    # No email service wired → approving records a failed action, never raises.
    _seed_google_account(session)
    confirmations = _confirmations(session, _executor(session))
    SendEmailTool().run(
        {"to": "a@b.com", "subject": "Hi", "body": "Yo"},
        _context(session, confirmations),
    )
    action = confirmations.list(1, pending_only=True)[0]
    result = confirmations.approve(1, action.id)
    assert result.status == "failed"
    assert "not configured" in result.result.lower()


def test_send_email_without_account_fails(session):
    # Email service present but no connected Google account.
    executor = _executor(session, email=FakeEmailService())
    confirmations = _confirmations(session, executor)
    SendEmailTool().run(
        {"to": "a@b.com", "subject": "Hi", "body": "Yo"},
        _context(session, confirmations),
    )
    action = confirmations.list(1, pending_only=True)[0]
    result = confirmations.approve(1, action.id)
    assert result.status == "failed"
    assert "account" in result.result.lower()


def test_fill_form_browser_error_is_failed(session):
    executor = _executor(session, browser=FakeBrowser(raises=True))
    confirmations = _confirmations(session, executor)
    FillFormTool().run(
        {"url": "https://x.com", "fields": {"#q": "hi"}},
        _context(session, confirmations),
    )
    action = confirmations.list(1, pending_only=True)[0]
    result = confirmations.approve(1, action.id)
    assert result.status == "failed"


def test_executor_never_raises_on_bad_payload(session):
    # Missing required args are reported, not raised.
    res = _executor(session, email=FakeEmailService()).execute(1, "send_email", {})
    assert not res.ok and "to" in res.message.lower()


# --- Browser read tools degrade without a browser ----------------------------


def test_browser_read_tools_without_browser(session):
    confirmations = _confirmations(session, _executor(session))
    ctx = _context(session, confirmations, browser=None)
    assert "not available" in ExtractStructuredDataTool().run(
        {"url": "https://x.com", "selectors": {"title": "h1"}}, ctx
    ).lower()
    assert "not available" in ScreenshotTool().run(
        {"url": "https://x.com"}, ctx
    ).lower()


# --- requires_confirmation override -----------------------------------------


def test_external_create_is_not_autonomous(session):
    # An external "create" (send_email) still requires confirmation.
    confirmations = _confirmations(session, _executor(session))
    msg = confirmations.handle(
        1,
        ProposedAction(
            tool_name="send_email",
            action_type="create",
            summary="Send email",
            payload={"to": "a@b.com", "subject": "x", "body": "y"},
            requires_confirmation=True,
        ),
    )
    assert "awaiting" in msg.lower()
    assert len(confirmations.list(1, pending_only=True)) == 1
