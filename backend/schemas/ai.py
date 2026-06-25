"""AI request/response schemas (DTOs).

Normalized data shapes shared across the AI stack:

- ``ChatMessage`` / ``ChatResponse`` are the provider-neutral contract every
  ``LLMProvider`` speaks, which is what makes providers interchangeable.
- The remaining models are the typed request/response bodies for the AI,
  conversation, and prompt API routes.

Mirrors backend/models/{conversation,message,system_prompt}.py for read views.
No business logic.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.action import PendingActionRead

# --- Provider-neutral tool contract ---------------------------------------


class ToolSpec(BaseModel):
    """A tool advertised to the provider (function-calling schema).

    ``parameters`` is a JSON Schema object describing the tool's arguments.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A provider's request to invoke a tool with parsed arguments."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


# --- Provider-neutral chat contract ---------------------------------------


class ChatMessage(BaseModel):
    """A single message in provider-neutral form.

    Carries the extra fields the tool-use loop needs: ``tool_calls`` on an
    assistant turn that requested tools, and ``tool_call_id`` / ``name`` on a
    ``role="tool"`` turn returning a result. Plain chat turns use only
    ``role`` + ``content``.
    """

    role: str  # "user" | "assistant" | "system" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class ChatResponse(BaseModel):
    """A provider's reply, normalized across Anthropic/OpenAI/Ollama.

    ``tool_calls`` is non-empty when the model wants tools run before it can
    answer. ``metadata`` is an open bag for provider-specific diagnostics
    (token usage, latency, finish reason, …) so new signals can be surfaced
    without changing this contract.
    """

    content: str
    provider: str
    model: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Chat endpoint --------------------------------------------------------


class ChatRequest(BaseModel):
    """Body for POST /ai/chat."""

    message: str = Field(min_length=1, max_length=8000)
    # Continue an existing thread, or omit to start a new one.
    conversation_id: int | None = None
    # Optional named system prompt to steer the assistant.
    system_prompt_id: int | None = None


class ToolInvocation(BaseModel):
    """A record of one tool the assistant ran, for surfacing in the UI."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    summary: str


class ChatResult(BaseModel):
    """Response for POST /ai/chat — the reply plus where it was persisted."""

    conversation_id: int
    message: "MessageRead"
    provider: str
    model: str
    tool_calls: list[ToolInvocation] = Field(default_factory=list)
    # Writes the assistant proposed this turn that await user confirmation.
    pending_actions: list[PendingActionRead] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Conversations & messages ---------------------------------------------


class MessageRead(BaseModel):
    """Read-view of a single conversation message."""

    id: int
    conversation_id: int
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class ConversationRead(BaseModel):
    """Read-view of a conversation (without its messages)."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    """A conversation together with its ordered messages."""

    messages: list[MessageRead] = []


class ConversationCreate(BaseModel):
    """Body for POST /conversations."""

    title: str | None = Field(default=None, max_length=200)


# --- System prompts -------------------------------------------------------


class SystemPromptRead(BaseModel):
    """Read-view of a selectable system prompt."""

    id: int
    name: str
    description: str | None = None
    system_prompt: str


# --- Diagnostics ----------------------------------------------------------


class AIHealth(BaseModel):
    """Active provider, configured model, and availability for diagnostics."""

    provider: str
    model: str
    available: bool


ChatResult.model_rebuild()
