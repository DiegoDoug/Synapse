"""DeepSeek provider — OpenAI-compatible client pointed at api.deepseek.com.

DeepSeek exposes the same Chat Completions contract as OpenAI, so the openai
SDK handles the wire protocol; we only swap the base URL and credentials.
Function calling (tool use) is supported by deepseek-chat and deepseek-reasoner.
The SDK is imported lazily so the backend boots without ``openai`` installed.
"""

import json
from collections.abc import Iterator
from typing import Any

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from backend.schemas.ai import ChatMessage, ChatResponse, ToolCall, ToolSpec

_PROVIDER = "deepseek"
_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(LLMProvider):
    """Calls the DeepSeek Chat Completions API via the OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider(self) -> str:
        return _PROVIDER

    @property
    def model(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        return True

    def available(self) -> bool:
        return bool(self._api_key)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int,
        temperature: float,
    ) -> ChatResponse:
        client = self._client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._to_openai(messages, system),
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

        choice = response.choices[0]
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=self._parse_args(tc.function.arguments),
            )
            for tc in (choice.message.tool_calls or [])
        ]
        usage = getattr(response, "usage", None)
        return ChatResponse(
            content=choice.message.content or "",
            provider=_PROVIDER,
            model=self._model,
            tool_calls=tool_calls,
            metadata={
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "finish_reason": getattr(choice, "finish_reason", None),
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
        client = self._client()
        try:
            stream = client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=self._to_openai(messages, system),
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

    # --- Internals ---------------------------------------------------------

    @staticmethod
    def _to_openai(
        messages: list[ChatMessage], system: str | None
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "content": m.content,
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                out.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    @staticmethod
    def _parse_args(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _client(self):
        if not self._api_key:
            raise ProviderAuthError("DEEPSEEK_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderUnavailableError(
                "The 'openai' package is not installed."
            ) from exc
        return OpenAI(api_key=self._api_key, base_url=_BASE_URL)

    @staticmethod
    def _normalize(exc: Exception) -> ProviderError:
        name = type(exc).__name__
        if "Authentication" in name or "Permission" in name:
            return ProviderAuthError(str(exc))
        if "RateLimit" in name:
            return ProviderRateLimitError(str(exc))
        return ProviderUnavailableError(str(exc))
