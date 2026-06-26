"""Construction helpers for services and integrations.

A single place that wires repositories + integrations into services, shared by
the API dependency layer, the scheduler, and background tasks so they all build
the notification stack the same way.
"""

from sqlmodel import Session, select

from backend.agents.registry import build_agent_registry
from backend.agents.runner import AgentRunner
from backend.config import Settings
from backend.integrations.ai.anthropic_provider import AnthropicProvider
from backend.integrations.ai.base import LLMProvider
from backend.integrations.ai.ollama_provider import OllamaProvider
from backend.integrations.ai.openai_provider import OpenAIProvider
from backend.integrations.browser.service import BrowserService
from backend.integrations.embeddings.base import EmbeddingModel
from backend.integrations.embeddings.sentence_transformer import (
    SentenceTransformerEmbedding,
)
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.integrations.telegram.bot import TelegramIntegration
from backend.integrations.vectorstore.base import VectorStore
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.integrations.vectorstore.qdrant_store import QdrantVectorStore
from backend.integrations.voice.kokoro import KokoroClient
from backend.integrations.voice.wakeword import OpenWakeWordClient
from backend.integrations.voice.whisper import WhisperClient
from backend.models.user import User
from backend.repositories.account_repository import AccountRepository
from backend.repositories.agent_run_repository import AgentRunRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.pending_action_repository import PendingActionRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.widget_repository import WidgetRepository
from backend.services.agent_service import AgentService
from backend.services.ai_service import AIService
from backend.services.calendar_service import CalendarService
from backend.services.confirmation_service import ConfirmationService
from backend.services.conversation_service import ConversationService
from backend.services.document_service import DocumentService
from backend.services.email_service import EmailService
from backend.services.knowledge_service import KnowledgeService
from backend.services.messaging_service import MessagingService
from backend.services.notification_service import NotificationService
from backend.services.stt_service import STTService
from backend.services.sync_service import SyncService
from backend.services.task_service import TaskService
from backend.services.tool_executor import ToolExecutor
from backend.services.tools.base import ToolContext
from backend.services.tools.read_tools import (
    GetCalendarEventsTool,
    GetNotificationsTool,
    SearchEmailsTool,
    SearchKnowledgeTool,
)
from backend.services.tools.registry import ToolRegistry
from backend.services.tools.web_tools import (
    ExtractStructuredDataTool,
    ScreenshotTool,
    WebFetchTool,
)
from backend.services.tools.write_tools import (
    CreateCalendarEventTool,
    CreateTaskTool,
    DeleteCalendarEventTool,
    DeleteTaskTool,
    FillFormTool,
    SendEmailTool,
    SendTelegramMessageTool,
    UpdateTaskTool,
    UpdateWidgetConfigTool,
)
from backend.services.tts_service import TTSService
from backend.services.voice_session import VoiceSession, VoiceSessionConfig
from backend.services.wakeword_service import WakeWordService
from backend.services.widget_service import WidgetService


def build_telegram_integration(settings: Settings) -> TelegramIntegration | None:
    """Return a Telegram client, or None when no bot token is configured."""
    if not settings.telegram_enabled:
        return None
    return TelegramIntegration(
        settings.telegram_bot_token, api_base=settings.telegram_api_base
    )


def build_notification_service(
    session: Session,
    settings: Settings | None = None,
    *,
    telegram: TelegramIntegration | None = None,
) -> NotificationService:
    """Assemble a NotificationService with its repositories and (optionally)
    a Telegram integration derived from settings."""
    chat_id = settings.telegram_default_chat_id if settings else None
    if telegram is None and settings is not None:
        telegram = build_telegram_integration(settings)
    return NotificationService(
        NotificationRepository(session),
        AccountRepository(session),
        EmailRepository(session),
        CalendarRepository(session),
        telegram=telegram,
        default_chat_id=chat_id,
    )


def build_sync_service(session: Session, settings: Settings) -> SyncService | None:
    """Assemble the Stage 2 SyncService, or None when Google isn't configured."""
    if not (settings.google_client_id and settings.google_client_secret):
        return None
    oauth = GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scopes=settings.google_scopes_list,
    )
    accounts = AccountRepository(session)
    sync_states = SyncStateRepository(session)
    email = EmailService(accounts, EmailRepository(session), sync_states, oauth)
    calendar = CalendarService(
        accounts, CalendarRepository(session), sync_states, oauth
    )
    return SyncService(email, calendar, sync_states)


def build_ai_provider(settings: Settings) -> LLMProvider:
    """Select and construct the active LLM provider from settings.

    Adding a new provider is one ``match`` arm plus its integration module.
    """
    provider = settings.ai_provider.lower()
    if provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    if provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    raise ValueError(f"Unknown AI provider: {settings.ai_provider!r}")


def build_conversation_service(session: Session) -> ConversationService:
    """Assemble a ConversationService with its repository."""
    return ConversationService(ConversationRepository(session))


# Knowledge-base integrations are cached as process singletons: the embedding
# model lazily loads a heavy local model on first use, and the in-process vector
# store holds the index in memory — both must be shared across requests.
_embedding_model: EmbeddingModel | None = None
_vector_store: VectorStore | None = None


def build_embedding_model(settings: Settings) -> EmbeddingModel:
    """Return the process-cached sentence-transformers embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformerEmbedding(
            settings.embedding_model,
            dimension_hint=settings.embedding_dimension,
        )
    return _embedding_model


def build_vector_store(settings: Settings) -> VectorStore:
    """Return the active vector store (Qdrant when configured + reachable,
    otherwise the process-cached in-process fallback)."""
    global _vector_store
    if settings.vector_backend.lower() == "qdrant":
        qdrant = QdrantVectorStore(
            settings.qdrant_url,
            settings.qdrant_collection,
            settings.embedding_dimension,
        )
        if qdrant.available():
            return qdrant
        # Fall through to the in-process store when Qdrant isn't reachable.
    if _vector_store is None:
        _vector_store = InProcessVectorStore()
    return _vector_store


def build_document_service(session: Session, settings: Settings) -> DocumentService:
    """Assemble the DocumentService over its repository + KB integrations."""
    return DocumentService(
        DocumentRepository(session),
        build_embedding_model(settings),
        build_vector_store(settings),
        embedding_model_name=settings.embedding_model,
        chunk_size=settings.knowledge_chunk_size,
        chunk_overlap=settings.knowledge_chunk_overlap,
    )


def build_knowledge_service(session: Session, settings: Settings) -> KnowledgeService:
    """Assemble the KnowledgeService (semantic search) over the KB integrations.

    Shares the process-cached embedding model + vector store with ingestion, so
    search reads the same index documents were written into."""
    return KnowledgeService(
        DocumentRepository(session),
        build_embedding_model(settings),
        build_vector_store(settings),
    )


# Voice model clients are cached as process singletons: each lazily loads a
# heavy local model on first use, so we must reuse one instance across requests
# rather than reload per call.
_whisper_client: WhisperClient | None = None
_kokoro_client: KokoroClient | None = None
_wakeword_client: OpenWakeWordClient | None = None


def build_whisper_client(settings: Settings) -> WhisperClient:
    global _whisper_client
    if _whisper_client is None:
        _whisper_client = WhisperClient(
            model_size=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _whisper_client


def build_kokoro_client(settings: Settings) -> KokoroClient:
    global _kokoro_client
    if _kokoro_client is None:
        _kokoro_client = KokoroClient(
            voice=settings.tts_voice, sample_rate=settings.tts_sample_rate
        )
    return _kokoro_client


def build_stt_service(settings: Settings) -> STTService:
    """Assemble the speech-to-text service over the cached Whisper client."""
    return STTService(build_whisper_client(settings))


def build_tts_service(settings: Settings) -> TTSService:
    """Assemble the text-to-speech service over the cached Kokoro client."""
    return TTSService(build_kokoro_client(settings))


def build_wakeword_client(settings: Settings) -> OpenWakeWordClient:
    global _wakeword_client
    if _wakeword_client is None:
        _wakeword_client = OpenWakeWordClient(model_name=settings.wake_word_model)
    return _wakeword_client


def build_wakeword_service(settings: Settings) -> WakeWordService:
    """Assemble the wake-word service over the cached openWakeWord client."""
    return WakeWordService(
        build_wakeword_client(settings), threshold=settings.wake_word_threshold
    )


def build_voice_session(settings: Settings) -> VoiceSession:
    """Assemble a per-connection wake-word session (wake word + STT + VAD)."""
    return VoiceSession(
        build_wakeword_service(settings),
        build_stt_service(settings),
        config=VoiceSessionConfig(
            sample_rate=settings.voice_sample_rate,
            silence_ms=settings.voice_silence_ms,
            max_utterance_ms=settings.voice_max_utterance_ms,
            silence_rms=settings.voice_silence_rms,
        ),
    )


def _build_google_services(
    session: Session, settings: Settings
) -> tuple[EmailService | None, CalendarService | None]:
    """Build OAuth-backed email + calendar services, or (None, None) if Google
    isn't configured."""
    if not (settings.google_client_id and settings.google_client_secret):
        return None, None
    oauth = GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scopes=settings.google_scopes_list,
    )
    accounts = AccountRepository(session)
    sync_states = SyncStateRepository(session)
    email = EmailService(accounts, EmailRepository(session), sync_states, oauth)
    calendar = CalendarService(
        accounts, CalendarRepository(session), sync_states, oauth
    )
    return email, calendar


def build_tool_executor(
    session: Session, settings: Settings | None = None
) -> ToolExecutor:
    """Assemble the ToolExecutor over the write services.

    Internal task/widget services are always present. External services (email,
    calendar, messaging) and the browser are wired when ``settings`` supplies the
    needed configuration; otherwise their handlers report unavailability at
    execution time rather than failing construction.
    """
    email = calendar = None
    messaging = None
    if settings is not None:
        email, calendar = _build_google_services(session, settings)
        messaging = MessagingService(
            build_telegram_integration(settings),
            default_chat_id=settings.telegram_default_chat_id or None,
        )
    return ToolExecutor(
        TaskService(TaskRepository(session)),
        WidgetService(WidgetRepository(session)),
        accounts=AccountRepository(session),
        email=email,
        calendar=calendar,
        messaging=messaging,
        browser=BrowserService(),
    )


def build_confirmation_service(
    session: Session, settings: Settings | None = None
) -> ConfirmationService:
    """Assemble the ConfirmationService + its ToolExecutor for the write flow."""
    return ConfirmationService(
        PendingActionRepository(session), build_tool_executor(session, settings)
    )


def build_tool_registry(
    session: Session,
    user_id: int,
    confirmations: ConfirmationService | None = None,
    knowledge: KnowledgeService | None = None,
) -> ToolRegistry:
    """Assemble the ToolRegistry scoped to a user + session.

    Read tools query repositories directly. Write tools (Stage 4.5) route
    through ``confirmations`` and are only included when one is supplied. The
    BrowserService is always provided; its Playwright dependency is lazy, so
    the web tool degrades to a friendly message when it is not installed. The
    knowledge-base search tool (Stage 5 RAG) is wired when ``knowledge`` is
    supplied and reports unavailable when embeddings aren't installed.
    """
    context = ToolContext(
        user_id=user_id,
        accounts=AccountRepository(session),
        emails=EmailRepository(session),
        events=CalendarRepository(session),
        notifications=NotificationRepository(session),
        browser=BrowserService(),
        confirmations=confirmations,
        knowledge=knowledge,
    )
    tools = [
        SearchEmailsTool(),
        GetCalendarEventsTool(),
        GetNotificationsTool(),
        WebFetchTool(),
        ExtractStructuredDataTool(),
        ScreenshotTool(),
    ]
    if knowledge is not None:
        tools.append(SearchKnowledgeTool())
    if confirmations is not None:
        tools += [
            # Internal CRUD
            CreateTaskTool(),
            UpdateTaskTool(),
            DeleteTaskTool(),
            UpdateWidgetConfigTool(),
            # External / outbound (confirmed)
            SendEmailTool(),
            CreateCalendarEventTool(),
            DeleteCalendarEventTool(),
            SendTelegramMessageTool(),
            # Browser write (confirmed)
            FillFormTool(),
        ]
    return ToolRegistry(tools, context)


def build_ai_service(
    session: Session, settings: Settings, user_id: int
) -> AIService:
    """Assemble the AIService: provider + conversation + prompts + tools.

    The same ``ConfirmationService`` instance backs both the write tools and the
    service, so proposals raised during a turn can be surfaced to the caller.
    External write tools are wired from ``settings`` (Google / Telegram).
    """
    confirmations = build_confirmation_service(session, settings)
    knowledge = build_knowledge_service(session, settings)
    return AIService(
        build_ai_provider(settings),
        build_conversation_service(session),
        SystemPromptRepository(session),
        max_tokens=settings.ai_max_tokens,
        temperature=settings.ai_temperature,
        tools=build_tool_registry(session, user_id, confirmations, knowledge),
        confirmations=confirmations,
    )


def build_agent_service(
    session: Session, settings: Settings, user_id: int
) -> AgentService:
    """Assemble the AgentService: agent catalogue + runner + tool registry.

    The runner records each run to the ``AgentRun`` audit trail. Agents drive
    the same user-scoped ``ToolRegistry`` the chat loop uses — wired with the
    confirmation flow (so creates run autonomously and destructive writes are
    logged as pending) and knowledge search — so no new side-effect path is
    introduced.
    """
    confirmations = build_confirmation_service(session, settings)
    knowledge = build_knowledge_service(session, settings)
    return AgentService(
        build_agent_registry(),
        AgentRunner(AgentRunRepository(session)),
        AgentRunRepository(session),
        build_tool_registry(session, user_id, confirmations, knowledge),
    )


def owner_user_id(session: Session) -> int | None:
    """Return the single owner user's id, or None before one exists."""
    return session.exec(select(User.id)).first()
