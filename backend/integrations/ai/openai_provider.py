"""OpenAI (GPT) provider — thin client over the OpenAI SDK.

The SDK is imported lazily so the backend boots without ``openai`` installed.
Unlike Anthropic, the system prompt is passed as a leading ``system`` message.
"""

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from backend.schemas.ai import ChatMessage, ChatResponse

_PROVIDER = "openai"


class OpenAIProvider(LLMProvider):
    """Calls the OpenAI Chat Completions API."""

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
        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=payload,
            )
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        return ChatResponse(
            content=choice.message.content or "",
            provider=_PROVIDER,
            model=self._model,
            metadata={
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "finish_reason": getattr(choice, "finish_reason", None),
            },
        )

    def _client(self):
        if not self._api_key:
            raise ProviderAuthError("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderUnavailableError(
                "The 'openai' package is not installed."
            ) from exc
        return OpenAI(api_key=self._api_key)

    @staticmethod
    def _normalize(exc: Exception) -> ProviderError:
        name = type(exc).__name__
        if "Authentication" in name or "Permission" in name:
            return ProviderAuthError(str(exc))
        if "RateLimit" in name:
            return ProviderRateLimitError(str(exc))
        return ProviderUnavailableError(str(exc))
