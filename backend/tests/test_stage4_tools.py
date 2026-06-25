"""Stage 4 (Major Feature 2) tests — read-only tools, tool-use loop, streaming.

Providers are faked in-memory: ``ToolUsingProvider`` exercises the tool loop,
``StreamingProvider`` exercises real token streaming. No network or SDKs.
"""

from datetime import UTC, datetime, timedelta

import pytest
from backend.integrations.ai.base import LLMProvider
from backend.main import app
from backend.models.account import Account
from backend.models.calendar_event import CalendarEvent
from backend.models.email_message import EmailMessage
from backend.models.notification import Notification
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.schemas.ai import ChatResponse, ToolCall
from backend.services.ai_service import AIService
from backend.services.conversation_service import ConversationService
from backend.services.tools.base import ToolContext
from backend.services.tools.read_tools import (
    GetCalendarEventsTool,
    GetNotificationsTool,
    SearchEmailsTool,
)
from backend.services.tools.registry import ToolRegistry
from backend.services.tools.web_tools import WebFetchTool
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


# --- Fake providers ----------------------------------------------------------


class ToolUsingProvider(LLMProvider):
    """Requests one tool on the first turn, then answers."""

    def __init__(self, tool_name: str = "get_notifications") -> None:
        self._tool_name = tool_name
        self.calls = 0

    @property
    def provider(self) -> str:
        return "toolfake"

    @property
    def model(self) -> str:
        return "tf-1"

    @property
    def supports_tools(self) -> bool:
        return True

    def chat(self, messages, *, system=None, tools=None, max_tokens, temperature):
        self.calls += 1
        used = any(m.role == "tool" for m in messages)
        if tools and not used:
            return ChatResponse(
                content="",
                provider=self.provider,
                model=self.model,
                tool_calls=[ToolCall(id="t1", name=self._tool_name, arguments={})],
            )
        return ChatResponse(content="All done.", provider=self.provider, model=self.model)


class StreamingProvider(LLMProvider):
    """No tools; streams two text deltas."""

    @property
    def provider(self) -> str:
        return "streamfake"

    @property
    def model(self) -> str:
        return "sf-1"

    def chat(self, messages, *, system=None, tools=None, max_tokens, temperature):
        return ChatResponse(content="Hello", provider=self.provider, model=self.model)

    def stream_chat(self, messages, *, system=None, max_tokens, temperature):
        yield "Hel"
        yield "lo"


# --- Builders / seeding ------------------------------------------------------


def _context(session: Session, user_id: int = 1) -> ToolContext:
    return ToolContext(
        user_id=user_id,
        accounts=AccountRepository(session),
        emails=EmailRepository(session),
        events=CalendarRepository(session),
        notifications=NotificationRepository(session),
    )


def _registry(session: Session) -> ToolRegistry:
    return ToolRegistry(
        [SearchEmailsTool(), GetCalendarEventsTool(), GetNotificationsTool(), WebFetchTool()],
        _context(session),
    )


def _ai(session: Session, provider: LLMProvider, *, tools: ToolRegistry | None):
    return AIService(
        provider,
        ConversationService(ConversationRepository(session)),
        SystemPromptRepository(session),
        max_tokens=128,
        temperature=0.5,
        tools=tools,
    )


def _seed_account(session: Session) -> Account:
    return AccountRepository(session).add(
        Account(user_id=1, provider="google", email="o@x", access_token="t")
    )


# --- API wiring --------------------------------------------------------------


def test_stream_route_registered():
    assert "/api/v1/ai/chat/stream" in set(app.openapi()["paths"])


# --- Read-only tools ---------------------------------------------------------


def test_search_emails_tool(session):
    account = _seed_account(session)
    EmailRepository(session).upsert(
        EmailMessage(
            account_id=account.id,
            external_id="m1",
            subject="Welcome aboard",
            sender="alice@example.com",
            is_read=False,
            received_at=datetime.now(UTC),
        )
    )
    result = SearchEmailsTool().run({"query": "welcome"}, _context(session))
    assert "Welcome aboard" in result
    assert "(unread)" in result
    # A non-matching query returns the empty sentinel.
    assert SearchEmailsTool().run({"query": "zzz"}, _context(session)) == (
        "No matching emails found."
    )


def test_get_calendar_events_tool(session):
    account = _seed_account(session)
    CalendarRepository(session).upsert(
        CalendarEvent(
            account_id=account.id,
            external_id="e1",
            summary="Standup",
            start=datetime.now(UTC) + timedelta(hours=2),
        )
    )
    result = GetCalendarEventsTool().run({}, _context(session))
    assert "Standup" in result


def test_get_notifications_tool(session):
    NotificationRepository(session).add(
        Notification(user_id=1, category="alert", title="Ping")
    )
    result = GetNotificationsTool().run({}, _context(session))
    assert "Ping" in result


def test_web_fetch_tool_without_browser(session):
    # No browser on the context → graceful message, never raises.
    out = WebFetchTool().run({"url": "https://example.com"}, _context(session))
    assert "not available" in out.lower()


# --- Registry ----------------------------------------------------------------


def test_registry_specs_and_unknown_tool(session):
    registry = _registry(session)
    names = {spec.name for spec in registry.specs()}
    assert {"search_emails", "get_calendar_events", "get_notifications", "web_fetch"} <= names
    assert "Unknown tool" in registry.execute("nope", {})


# --- Tool-use loop -----------------------------------------------------------


def test_chat_runs_tool_loop_and_records_invocations(session):
    NotificationRepository(session).add(
        Notification(user_id=1, category="alert", title="Ping")
    )
    provider = ToolUsingProvider()
    service = _ai(session, provider, tools=_registry(session))

    result = service.chat(1, message="any notifications?")
    assert result.message.content == "All done."
    assert provider.calls == 2  # tool turn + final answer
    assert [inv.name for inv in result.tool_calls] == ["get_notifications"]
    assert "Ping" in result.tool_calls[0].summary

    # A tool step is persisted alongside the user + assistant turns.
    detail = service._conversations.get(1, result.conversation_id)
    roles = [m.role for m in detail.messages]
    assert roles == ["user", "tool", "assistant"]


def test_tools_skipped_when_provider_unsupported(session):
    # StreamingProvider.supports_tools is False → no tool loop, single call.
    service = _ai(session, StreamingProvider(), tools=_registry(session))
    result = service.chat(1, message="hi")
    assert result.tool_calls == []
    assert result.message.content == "Hello"


# --- Streaming ---------------------------------------------------------------


def test_stream_emits_token_events(session):
    service = _ai(session, StreamingProvider(), tools=None)
    events = list(service.stream(1, message="hi"))
    types = [e["type"] for e in events]
    assert types[0] == "conversation"
    assert types[-1] == "done"
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert tokens == "Hello"

    # The streamed answer is persisted as the assistant message.
    detail = service._conversations.get(1, events[-1]["conversation_id"])
    assert detail.messages[-1].content == "Hello"


def test_stream_emits_tool_call_events(session):
    NotificationRepository(session).add(
        Notification(user_id=1, category="alert", title="Ping")
    )
    service = _ai(session, ToolUsingProvider(), tools=_registry(session))
    events = list(service.stream(1, message="any notifications?"))
    types = [e["type"] for e in events]
    assert "tool_call" in types
    tool_event = next(e for e in events if e["type"] == "tool_call")
    assert tool_event["name"] == "get_notifications"
    answer = "".join(e["text"] for e in events if e["type"] == "token")
    assert answer.strip() == "All done."


def test_stream_unowned_conversation_emits_error(session):
    service = _ai(session, StreamingProvider(), tools=None)
    events = list(service.stream(2, message="hi", conversation_id=999))
    assert events == [{"type": "error", "detail": "Conversation not found"}]
