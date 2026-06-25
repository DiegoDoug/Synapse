"""Anthropic (Claude) provider — thin client over the Anthropic SDK.

Supports the tool-use loop (native ``tool_use`` blocks) and token streaming for
the final answer. The SDK is imported lazily so the backend boots even when
``anthropic`` is not installed or no key is configured.
"""

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
            "system": system or "",
            "messages": self._to_anthropic(messages),
        }
        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        try:
            response = client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )

        usage = getattr(response, "usage", None)
        return ChatResponse(
            content="".join(text_parts),
            provider=_PROVIDER,
            model=self._model,
            tool_calls=tool_calls,
            metadata={
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "stop_reason": getattr(response, "stop_reason", None),
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
            with client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "",
                messages=self._to_anthropic(messages),
            ) as stream:
                yield from stream.text_stream
        except Exception as exc:  # noqa: BLE001 — normalize SDK errors
            raise self._normalize(exc) from exc

    # --- Internals ---------------------------------------------------------

    @staticmethod
    def _to_anthropic(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Translate provider-neutral messages into Anthropic's format."""
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content,
                            }
                        ],
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                blocks.extend(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                    for tc in m.tool_calls
                )
                out.append({"role": "assistant", "content": blocks})
            elif m.role in ("user", "assistant"):
                out.append({"role": m.role, "content": m.content})
        return out

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
