"""Construction helpers for services and integrations.

A single place that wires repositories + integrations into services, shared by
the API dependency layer, the scheduler, and background tasks so they all build
the notification stack the same way.
"""

from sqlmodel import Session, select

from backend.config import Settings
from backend.integrations.ai.anthropic_provider import AnthropicProvider
from backend.integrations.ai.base import LLMProvider
from backend.integrations.ai.ollama_provider import OllamaProvider
from backend.integrations.ai.openai_provider import OpenAIProvider
from backend.integrations.browser.service import BrowserService
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.integrations.telegram.bot import TelegramIntegration
from backend.integrations.voice.kokoro import KokoroClient
from backend.integrations.voice.whisper import WhisperClient
from backend.models.user import User
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.pending_action_repository import PendingActionRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.widget_repository import WidgetRepository
from backend.services.ai_service import AIService
from backend.services.calendar_service import CalendarService
from backend.services.confirmation_service import ConfirmationService
from backend.services.conversation_service import ConversationService
from backend.services.email_service import EmailService
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


# Voice model clients are cached as process singletons: each lazily loads a
# heavy local model on first use, so we must reuse one instance across requests
# rather than reload per call.
_whisper_client: WhisperClient | None = None
_kokoro_client: KokoroClient | None = None


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
) -> ToolRegistry:
    """Assemble the ToolRegistry scoped to a user + session.

    Read tools query repositories directly. Write tools (Stage 4.5) route
    through ``confirmations`` and are only included when one is supplied. The
    BrowserService is always provided; its Playwright dependency is lazy, so
    the web tool degrades to a friendly message when it is not installed.
    """
    context = ToolContext(
        user_id=user_id,
        accounts=AccountRepository(session),
        emails=EmailRepository(session),
        events=CalendarRepository(session),
        notifications=NotificationRepository(session),
        browser=BrowserService(),
        confirmations=confirmations,
    )
    tools = [
        SearchEmailsTool(),
        GetCalendarEventsTool(),
        GetNotificationsTool(),
        WebFetchTool(),
        ExtractStructuredDataTool(),
        ScreenshotTool(),
    ]
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
    return AIService(
        build_ai_provider(settings),
        build_conversation_service(session),
        SystemPromptRepository(session),
        max_tokens=settings.ai_max_tokens,
        temperature=settings.ai_temperature,
        tools=build_tool_registry(session, user_id, confirmations),
        confirmations=confirmations,
    )


def owner_user_id(session: Session) -> int | None:
    """Return the single owner user's id, or None before one exists."""
    return session.exec(select(User.id)).first()
