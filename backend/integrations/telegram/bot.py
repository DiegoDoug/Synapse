"""Telegram Bot API integration (integration layer).

Thin HTTP wrapper over the Telegram Bot API. Returns raw API payloads and
raises on transport/HTTP errors; composing messages, deciding what to send, and
routing inbound commands are the service layer's concern. No business logic, no
database access.

Uses httpx directly (already a project dependency) rather than a heavier bot
framework, keeping the integration a true thin client per the architecture
contract.
"""

import httpx

from backend.integrations.base import Integration

_DEFAULT_TIMEOUT = 10.0


class TelegramError(RuntimeError):
    """Raised when the Telegram Bot API reports a failure."""


class TelegramIntegration(Integration):
    """HTTP client for a single Telegram bot, identified by its token."""

    def __init__(
        self,
        token: str,
        *,
        api_base: str = "https://api.telegram.org",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = f"{api_base.rstrip('/')}/bot{token}"
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return "telegram"

    def get_me(self) -> dict:
        """Return the bot account (used to verify the token)."""
        return self._call("getMe")

    def send_message(self, chat_id: str, text: str) -> dict:
        """Send a text message to a chat. Returns the sent message payload."""
        return self._call(
            "sendMessage",
            {"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        )

    def get_updates(self, offset: int | None = None, *, timeout: int = 0) -> list[dict]:
        """Poll for inbound updates. ``offset`` confirms prior updates."""
        params: dict[str, int] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        return self._call("getUpdates", params)

    # --- Internals ---------------------------------------------------------

    def _call(self, method: str, payload: dict | None = None):
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(f"{self._base_url}/{method}", json=payload or {})
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:  # network / non-2xx
            raise TelegramError(f"Telegram {method} failed: {exc}") from exc
        if not body.get("ok", False):
            raise TelegramError(
                f"Telegram {method} error: {body.get('description', 'unknown')}"
            )
        return body.get("result")
