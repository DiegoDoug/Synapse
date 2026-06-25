"""Messaging service — outbound Telegram sends for the assistant.

Business logic for the ``send_telegram_message`` write tool: it picks the target
chat (explicit or the configured default) and delegates the HTTP call to the
``TelegramIntegration``. Mirrors how ``NotificationService`` delivers alerts, but
scoped to free-form messages the assistant proposes. No database access.
"""

from __future__ import annotations

from backend.integrations.telegram.bot import TelegramIntegration


class MessagingService:
    """Send free-form Telegram messages on the user's behalf."""

    def __init__(
        self,
        telegram: TelegramIntegration | None,
        *,
        default_chat_id: str | None = None,
    ) -> None:
        self._telegram = telegram
        self._default_chat_id = default_chat_id

    @property
    def available(self) -> bool:
        """True when a bot is configured and a chat can be resolved."""
        return self._telegram is not None and bool(self._default_chat_id)

    def send_telegram_message(self, text: str, *, chat_id: str | None = None) -> str:
        """Send ``text`` to ``chat_id`` (or the default). Returns a status note.

        Raises ``TelegramError`` from the integration on a transport/API
        failure, which the executor records as a failed action.
        """
        if self._telegram is None:
            raise ValueError("Telegram is not configured.")
        target = chat_id or self._default_chat_id
        if not target:
            raise ValueError("No Telegram chat id available to send to.")
        self._telegram.send_message(target, text)
        return f"Message sent to chat {target}."
