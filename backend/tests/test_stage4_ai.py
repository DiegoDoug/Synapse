"""Stage 4 (Major Feature 1) tests — AI provider routing, chat, persistence.

A FakeProvider implements the LLMProvider contract in-memory, so the whole
service stack is exercised without any network or SDK dependency.
"""

import pytest
from backend.integrations.ai.base import LLMProvider, ProviderUnavailableError
from backend.main import app
from backend.models.system_prompt import SystemPrompt
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.schemas.ai import ChatMessage, ChatResponse
from backend.services.ai_service import DEFAULT_SYSTEM_PROMPT, AIService
from backend.services.conversation_service import ConversationService
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


class FakeProvider(LLMProvider):
    """Records the system prompt + messages it received and echoes a reply."""

    def __init__(self, *, available: bool = True, fail: bool = False) -> None:
        self._available = available
        self._fail = fail
        self.last_system: str | None = None
        self.last_messages: list[ChatMessage] = []

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-1"

    def available(self) -> bool:
        return self._available

    def chat(
        self, messages, *, system=None, tools=None, max_tokens, temperature
    ) -> ChatResponse:
        if self._fail:
            raise ProviderUnavailableError("boom")
        self.last_system = system
        self.last_messages = list(messages)
        return ChatResponse(
            content=f"echo: {messages[-1].content}",
            provider=self.provider,
            model=self.model,
            metadata={"tokens": 7},
        )


def _ai_service(session: Session, provider: LLMProvider) -> AIService:
    return AIService(
        provider,
        ConversationService(ConversationRepository(session)),
        SystemPromptRepository(session),
        max_tokens=128,
        temperature=0.5,
    )


# --- API wiring --------------------------------------------------------------


def test_ai_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/ai/chat" in paths
    assert "/api/v1/ai/health" in paths
    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}" in paths
    assert "/api/v1/prompts" in paths


# --- Chat orchestration + persistence ----------------------------------------


def test_chat_creates_conversation_and_persists_turns(session):
    provider = FakeProvider()
    service = _ai_service(session, provider)

    result = service.chat(1, message="Hello there")
    assert result is not None
    assert result.message.role == "assistant"
    assert result.message.content == "echo: Hello there"
    assert result.provider == "fake"
    assert result.model == "fake-1"
    assert result.metadata == {"tokens": 7}

    # Both turns persisted in order, titled from the first user message.
    detail = service._conversations.get(1, result.conversation_id)
    assert [m.role for m in detail.messages] == ["user", "assistant"]
    assert detail.title == "Hello there"


def test_chat_continues_existing_conversation(session):
    provider = FakeProvider()
    service = _ai_service(session, provider)

    first = service.chat(1, message="One")
    second = service.chat(
        1, message="Two", conversation_id=first.conversation_id
    )
    assert second.conversation_id == first.conversation_id

    # History sent to the provider includes the prior turns.
    contents = [m.content for m in provider.last_messages]
    assert contents == ["One", "echo: One", "Two"]


def test_chat_rejects_unowned_conversation(session):
    service = _ai_service(session, FakeProvider())
    mine = service.chat(1, message="Mine")
    # A different user cannot post into it.
    assert service.chat(2, message="hi", conversation_id=mine.conversation_id) is None
    # Unknown id is also a miss.
    assert service.chat(1, message="hi", conversation_id=9999) is None


def test_chat_uses_default_system_prompt(session):
    provider = FakeProvider()
    service = _ai_service(session, provider)
    service.chat(1, message="Hi")
    assert provider.last_system == DEFAULT_SYSTEM_PROMPT


def test_chat_uses_selected_system_prompt(session):
    prompt = SystemPromptRepository(session).add(
        SystemPrompt(name="Terse", system_prompt="Answer in one word.")
    )
    provider = FakeProvider()
    service = _ai_service(session, provider)
    service.chat(1, message="Hi", system_prompt_id=prompt.id)
    assert provider.last_system == "Answer in one word."


def test_provider_failure_propagates(session):
    service = _ai_service(session, FakeProvider(fail=True))
    with pytest.raises(ProviderUnavailableError):
        service.chat(1, message="Hi")


# --- Prompts + diagnostics ---------------------------------------------------


def test_list_prompts(session):
    SystemPromptRepository(session).add(
        SystemPrompt(name="Tutor", description="Teaches", system_prompt="Teach.")
    )
    service = _ai_service(session, FakeProvider())
    prompts = service.list_prompts()
    assert len(prompts) == 1
    assert prompts[0].name == "Tutor"


def test_health_reports_active_provider(session):
    service = _ai_service(session, FakeProvider(available=False))
    health = service.health()
    assert health.provider == "fake"
    assert health.model == "fake-1"
    assert health.available is False


# --- Conversation service ----------------------------------------------------


def test_conversation_create_and_list(session):
    service = ConversationService(ConversationRepository(session))
    created = service.create(1, title="My thread")
    assert created.title == "My thread"
    listed = service.list(1)
    assert len(listed) == 1
    assert listed[0].id == created.id


def test_get_conversation_scoped_to_user(session):
    service = ConversationService(ConversationRepository(session))
    mine = service.create(1, title="Mine")
    assert service.get(2, mine.id) is None
    assert service.get(1, mine.id) is not None
