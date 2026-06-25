"""Ollama provider — thin client over the local Ollama HTTP API.

Uses httpx directly (already a backend dependency) against a local Ollama
server's ``/api/chat`` endpoint. No API key: availability is "is a base URL
configured", and reachability is only known at call time.
"""

import json
from collections.abc import Iterator

import httpx

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderError,
    ProviderUnavailableError,
)
from backend.schemas.ai import ChatMessage, ChatResponse, ToolSpec

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
        tools: list[ToolSpec] | None = None,
        max_tokens: int,
        temperature: float,
    ) -> ChatResponse:
        # Tools are intentionally not advertised: tool use varies by local
        # model, and Anthropic is the primary tool provider. ``tools`` is
        # accepted for interface parity and ignored here.
        body = {
            "model": self._model,
            "messages": self._to_ollama(messages, system),
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

    def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int,
        temperature: float,
    ) -> Iterator[str]:
        body = {
            "model": self._model,
            "messages": self._to_ollama(messages, system),
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            with httpx.stream(
                "POST", f"{self._base_url}/api/chat", json=body, timeout=_TIMEOUT
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            raise self._normalize(exc) from exc

    @staticmethod
    def _to_ollama(
        messages: list[ChatMessage], system: str | None
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        if system:
            out.append({"role": "system", "content": system})
        # Tool turns (if any leaked in) are flattened to plain context lines.
        for m in messages:
            role = m.role if m.role in ("user", "assistant", "system") else "user"
            out.append({"role": role, "content": m.content})
        return out

    @staticmethod
    def _normalize(exc: httpx.HTTPError) -> ProviderError:
        return ProviderUnavailableError(
            f"Ollama request failed ({type(exc).__name__}): {exc}"
        )
