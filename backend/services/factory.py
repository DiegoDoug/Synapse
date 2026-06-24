"""Construction helpers for services and integrations.

A single place that wires repositories + integrations into services, shared by
the API dependency layer, the scheduler, and background tasks so they all build
the notification stack the same way.
"""

from sqlmodel import Session, select

from backend.config import Settings
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.integrations.telegram.bot import TelegramIntegration
from backend.models.user import User
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.services.calendar_service import CalendarService
from backend.services.email_service import EmailService
from backend.services.notification_service import NotificationService
from backend.services.sync_service import SyncService


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


def owner_user_id(session: Session) -> int | None:
    """Return the single owner user's id, or None before one exists."""
    return session.exec(select(User.id)).first()
