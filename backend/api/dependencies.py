"""FastAPI dependency-injection providers.

Wires sessions, the current user, the Google OAuth client, and the Stage 2
services together. Routes depend on these factories rather than constructing
services directly, keeping wiring in one place.
"""

from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from backend.config import Settings, get_settings
from backend.database import get_session
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.models.user import User
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.ai_service import AIService
from backend.services.calendar_service import CalendarService
from backend.services.confirmation_service import ConfirmationService
from backend.services.connection_service import ConnectionService
from backend.services.conversation_service import ConversationService
from backend.services.email_service import EmailService
from backend.services.factory import (
    build_ai_service,
    build_confirmation_service,
    build_conversation_service,
    build_notification_service,
)
from backend.services.notification_service import NotificationService
from backend.services.sync_service import SyncService
from backend.services.task_service import TaskService

# Default owner identity for the single-user Personal OS. A dedicated auth
# stage will replace this; for now connections attach to the one owner account.
_DEFAULT_OWNER_EMAIL = "owner@localhost"
_DEFAULT_OWNER_NAME = "Owner"


def get_current_user_id(session: Session = Depends(get_session)) -> int:
    """Return the owner user's id, creating the owner on first use."""
    user = session.exec(select(User)).first()
    if user is None:
        user = User(email=_DEFAULT_OWNER_EMAIL, name=_DEFAULT_OWNER_NAME)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


def get_google_oauth_client(
    settings: Settings = Depends(get_settings),
) -> GoogleOAuthClient:
    """Provide a configured Google OAuth client or fail clearly."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured (set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET).",
        )
    return GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scopes=settings.google_scopes_list,
    )


def get_connection_service(
    session: Session = Depends(get_session),
    oauth: GoogleOAuthClient = Depends(get_google_oauth_client),
    user_id: int = Depends(get_current_user_id),
) -> ConnectionService:
    return ConnectionService(AccountRepository(session), oauth, user_id)


def get_email_service(
    session: Session = Depends(get_session),
    oauth: GoogleOAuthClient = Depends(get_google_oauth_client),
) -> EmailService:
    return EmailService(
        AccountRepository(session),
        EmailRepository(session),
        SyncStateRepository(session),
        oauth,
    )


def get_calendar_service(
    session: Session = Depends(get_session),
    oauth: GoogleOAuthClient = Depends(get_google_oauth_client),
) -> CalendarService:
    return CalendarService(
        AccountRepository(session),
        CalendarRepository(session),
        SyncStateRepository(session),
        oauth,
    )


def get_sync_service(
    session: Session = Depends(get_session),
    email: EmailService = Depends(get_email_service),
    calendar: CalendarService = Depends(get_calendar_service),
) -> SyncService:
    return SyncService(email, calendar, SyncStateRepository(session))


def get_notification_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> NotificationService:
    # Composition reads already-synced rows (no OAuth needed); the factory also
    # wires the optional Telegram integration for delivery endpoints.
    return build_notification_service(session, settings)


def get_conversation_service(
    session: Session = Depends(get_session),
) -> ConversationService:
    return build_conversation_service(session)


def get_ai_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user_id: int = Depends(get_current_user_id),
) -> AIService:
    # Builds the active provider + user-scoped read & write tools. No network
    # call happens at construction.
    return build_ai_service(session, settings, user_id)


def get_task_service(
    session: Session = Depends(get_session),
) -> TaskService:
    return TaskService(TaskRepository(session))


def get_confirmation_service(
    session: Session = Depends(get_session),
) -> ConfirmationService:
    # The pending-action lifecycle + its ToolExecutor. Used by the confirmation
    # routes to approve/reject proposals raised during chat.
    return build_confirmation_service(session)
