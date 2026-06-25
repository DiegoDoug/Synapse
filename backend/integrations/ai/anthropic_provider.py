"""Anthropic (Claude) provider — thin client over the Anthropic SDK.

The SDK is imported lazily so the backend boots even when ``anthropic`` is not
installed or no key is configured; construction simply requires a key, and the
import happens on first use.
"""

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from backend.schemas.ai import ChatMessage, ChatResponse

_PROVIDER = "anthropic"


class AnthropicProvider(LLMProvider):
    """Calls the Anthropic Messages API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider(self) -> str:
        return _PROVIDER

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        return bool(self._api_key)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int,
        temperature: float,
    ) -> ChatResponse:
        client = self._client()
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "",
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in messages
                    if m.role in ("user", "assistant")
                ],
            )
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        usage = getattr(response, "usage", None)
        return ChatResponse(
            content=text,
            provider=_PROVIDER,
            model=self._model,
            metadata={
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "stop_reason": getattr(response, "stop_reason", None),
            },
        )

    def _client(self):
        if not self._api_key:
            raise ProviderAuthError("ANTHROPIC_API_KEY is not configured.")
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderUnavailableError(
                "The 'anthropic' package is not installed."
            ) from exc
        return Anthropic(api_key=self._api_key)

    @staticmethod
    def _normalize(exc: Exception) -> ProviderError:
        name = type(exc).__name__
        if "Authentication" in name or "Permission" in name:
            return ProviderAuthError(str(exc))
        if "RateLimit" in name:
            return ProviderRateLimitError(str(exc))
        return ProviderUnavailableError(str(exc))
