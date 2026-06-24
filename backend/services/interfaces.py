"""Service layer contracts (interfaces).

Explicit, dependency-injection-friendly contracts for the Stage 2 services.
Concrete implementations (added in the Gmail and Calendar phases) orchestrate
repositories and integrations behind these interfaces, keeping routes and
other services decoupled from implementation details.

Methods are synchronous to match the existing SQLModel session layer
(`backend.database.get_session`), which runs in FastAPI's threadpool.
"""

from abc import ABC, abstractmethod

from backend.schemas.calendar import EventDetail, EventSummary
from backend.schemas.connection import AuthorizationUrlResponse, ConnectionRead
from backend.schemas.email import EmailDetail, EmailSummary
from backend.schemas.notification import (
    ComposeResult,
    NotificationCounts,
    NotificationCreate,
    NotificationRead,
)
from backend.schemas.sync import SyncResult, SyncStatusRead


class ConnectionServiceInterface(ABC):
    """Manage external account connections and their OAuth credentials."""

    @abstractmethod
    def build_authorization_url(self, user_id: int) -> AuthorizationUrlResponse:
        """Return the provider URL the user visits to grant access."""

    @abstractmethod
    def complete_authorization(self, code: str, state: str) -> ConnectionRead:
        """Exchange an authorization code for tokens and persist the account."""

    @abstractmethod
    def list_connections(self, user_id: int) -> list[ConnectionRead]:
        """List the user's connected accounts (without tokens)."""

    @abstractmethod
    def disconnect(self, account_id: int) -> None:
        """Revoke and remove a connected account."""


class EmailServiceInterface(ABC):
    """Read access to synced email plus on-demand email synchronization."""

    @abstractmethod
    def list_messages(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[EmailSummary]:
        """List synced messages for an account, newest first."""

    @abstractmethod
    def get_message(self, account_id: int, message_id: int) -> EmailDetail | None:
        """Return a single synced message, or None if not found."""

    @abstractmethod
    def sync(self, account_id: int) -> SyncResult:
        """Pull new/changed messages from the provider into local storage."""


class CalendarServiceInterface(ABC):
    """Read access to synced events plus on-demand calendar synchronization."""

    @abstractmethod
    def list_events(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EventSummary]:
        """List synced events for an account, soonest first."""

    @abstractmethod
    def get_event(self, account_id: int, event_id: int) -> EventDetail | None:
        """Return a single synced event, or None if not found."""

    @abstractmethod
    def sync(self, account_id: int) -> SyncResult:
        """Pull new/changed events from the provider into local storage."""


class NotificationServiceInterface(ABC):
    """Compose, list, and update in-app notifications for a user."""

    @abstractmethod
    def list(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[NotificationRead]:
        """List a user's notifications, newest first."""

    @abstractmethod
    def counts(self, user_id: int) -> NotificationCounts:
        """Return unread/total counts for the notification badge."""

    @abstractmethod
    def create(self, user_id: int, data: NotificationCreate) -> NotificationRead:
        """Create a manual in-app notification."""

    @abstractmethod
    def mark_read(self, user_id: int, notification_id: int) -> NotificationRead | None:
        """Mark one notification read, or None if it does not belong to the user."""

    @abstractmethod
    def mark_all_read(self, user_id: int) -> int:
        """Mark every unread notification read; return how many changed."""

    @abstractmethod
    def compose(self, user_id: int) -> ComposeResult:
        """Compose notifications from recently synced emails and events."""


class SyncServiceInterface(ABC):
    """Coordinate synchronization across all resources of an account."""

    @abstractmethod
    def sync_account(self, account_id: int) -> list[SyncResult]:
        """Synchronize every supported resource for an account."""

    @abstractmethod
    def get_status(self, account_id: int) -> list[SyncStatusRead]:
        """Return the current sync checkpoint for each resource."""
