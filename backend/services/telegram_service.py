"""Telegram inbound command handling (service layer).

Polls the Telegram integration for updates and routes simple commands to
replies, delegating data lookups to the NotificationService. Holds the update
offset in memory so repeated polls don't re-handle already-confirmed updates.

This is business logic; the HTTP calls live in TelegramIntegration.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TypeVar

from sqlmodel import Session

from backend.config import Settings
from backend.integrations.telegram.bot import TelegramIntegration
from backend.services.factory import build_notification_service, owner_user_id
from backend.services.notification_service import NotificationService

_HELP = (
    "Synapse bot commands:\n"
    "/help — show this help\n"
    "/summary — today's activity summary\n"
    "/unread — unread notification count"
)

T = TypeVar("T")

SessionFactory = Callable[[], AbstractContextManager[Session]]


class TelegramService:
    """Route inbound Telegram commands to notification-center data."""

    def __init__(
        self,
        integration: TelegramIntegration,
        session_factory: SessionFactory,
        settings: Settings,
    ) -> None:
        self._tg = integration
        self._session_factory = session_factory
        self._settings = settings
        self._offset: int | None = None

    def poll(self) -> int:
        """Fetch and handle new command messages. Returns how many were handled."""
        handled = 0
        for update in self._tg.get_updates(offset=self._offset):
            self._offset = int(update["update_id"]) + 1
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            if not text.startswith("/"):
                continue
            chat = message.get("chat") or {}
            chat_id = str(chat.get("id") or self._settings.telegram_default_chat_id)
            reply = self._reply_for(text)
            if reply and chat_id:
                self._tg.send_message(chat_id, reply)
                handled += 1
        return handled

    # --- Internals ---------------------------------------------------------

    def _reply_for(self, text: str) -> str | None:
        command = text.split()[0].lstrip("/").split("@")[0].lower()
        if command in ("start", "help"):
            return _HELP
        if command == "summary":
            return self._with_service(
                lambda svc, uid: svc.summary_text(uid)
                if uid is not None
                else "No activity yet."
            )
        if command == "unread":
            return self._with_service(
                lambda svc, uid: f"You have {svc.counts(uid).unread} unread "
                "notification(s)."
                if uid is not None
                else "No notifications yet."
            )
        return f"Unknown command: {text.split()[0]}. Send /help."

    def _with_service(
        self, fn: Callable[[NotificationService, int | None], T]
    ) -> T:
        with self._session_factory() as session:
            service = build_notification_service(session, self._settings)
            return fn(service, owner_user_id(session))
