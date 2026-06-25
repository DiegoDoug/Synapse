"""LLM provider contract and error hierarchy.

``LLMProvider`` is the single swap point that makes Anthropic, OpenAI, and
Ollama interchangeable: each takes provider-neutral ``ChatMessage`` objects and
returns a normalized ``ChatResponse``. Methods are synchronous to match the
existing service/route layer (FastAPI runs them in its threadpool).

``chat`` optionally accepts ``tools``; when supplied and supported, the
response may carry ``tool_calls`` for the service's tool-use loop. ``stream_chat``
yields text deltas for the final (tool-free) answer; the default implementation
falls back to a single chunk so providers without native streaming still work.

Providers raise the ``ProviderError`` hierarchy so the service layer can map
vendor failures onto clean HTTP responses without leaking SDK internals.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from backend.schemas.ai import ChatMessage, ChatResponse, ToolSpec


class ProviderError(RuntimeError):
    """Base class for any LLM provider failure."""


class ProviderAuthError(ProviderError):
    """Missing or invalid credentials."""


class ProviderRateLimitError(ProviderError):
    """Rate limited or quota exceeded."""


class ProviderUnavailableError(ProviderError):
    """Provider unreachable, timed out, or returned a server error."""


class LLMProvider(ABC):
    """Contract every chat provider implements."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Stable provider identifier (e.g. "anthropic")."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        """The configured model id this provider will call."""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int,
        temperature: float,
    ) -> ChatResponse:
        """Send a turn-by-turn message list and return the assistant reply.

        When ``tools`` are supplied and supported, the reply may request tool
        calls instead of (or alongside) text.
        """
        raise NotImplementedError

    def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int,
        temperature: float,
    ) -> Iterator[str]:
        """Yield the final answer as text deltas (no tools).

        Default: a single chunk from ``chat``. Providers override for real
        token streaming.
        """
        yield self.chat(
            messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        ).content

    @property
    def supports_tools(self) -> bool:
        """Whether this provider can use tools. Default False; override True."""
        return False

    def available(self) -> bool:
        """Whether the provider is configured enough to attempt a call.

        Default True; credential-backed providers override to report on the
        presence of an API key. Used by diagnostics, not enforced here.
        """
        return True
