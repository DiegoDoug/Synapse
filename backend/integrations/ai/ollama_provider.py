"""Ollama provider — thin client over the local Ollama HTTP API.

Uses httpx directly (already a backend dependency) against a local Ollama
server's ``/api/chat`` endpoint. No API key: availability is "is a base URL
configured", and reachability is only known at call time.
"""

import httpx

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderError,
    ProviderUnavailableError,
)
from backend.schemas.ai import ChatMessage, ChatResponse

_PROVIDER = "ollama"
_TIMEOUT = 120.0


class OllamaProvider(LLMProvider):
    """Calls a local Ollama server's chat endpoint."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider(self) -> str:
        return _PROVIDER

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        return bool(self._base_url)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int,
        temperature: float,
    ) -> ChatResponse:
        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)

        body = {
            "model": self._model,
            "messages": payload,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            response = httpx.post(
                f"{self._base_url}/api/chat", json=body, timeout=_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise self._normalize(exc) from exc

        return ChatResponse(
            content=data.get("message", {}).get("content", ""),
            provider=_PROVIDER,
            model=self._model,
            metadata={
                "eval_count": data.get("eval_count"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "done_reason": data.get("done_reason"),
            },
        )

    @staticmethod
    def _normalize(exc: httpx.HTTPError) -> ProviderError:
        return ProviderUnavailableError(
            f"Ollama request failed ({type(exc).__name__}): {exc}"
        )
