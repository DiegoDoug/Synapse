"""AI service — provider routing, prompt assembly, tool-use loop, streaming.

The single entry point for AI chat. It selects the active provider (injected),
assembles the system prompt + conversation history, runs the read-only tool-use
loop when tools are available, and persists both the user turn and the
assistant reply via ``ConversationService``.

Providers are never imported by routes — only this service talks to them, and
only through the ``LLMProvider`` interface, which keeps them swappable. Read
tools run autonomously inside the tool-use loop; write tools (Stage 4.5) route
proposals through the ``ConfirmationService`` — creates execute immediately,
updates and deletes surface as pending actions for the user to approve.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from backend.integrations.ai.base import LLMProvider
from backend.models.conversation import Conversation
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.schemas.action import PendingActionRead
from backend.schemas.ai import (
    AIHealth,
    ChatMessage,
    ChatResult,
    MessageRead,
    SystemPromptRead,
    ToolCall,
    ToolInvocation,
)
from backend.services.confirmation_service import ConfirmationService
from backend.services.conversation_service import ConversationService
from backend.services.interfaces import AIServiceInterface
from backend.services.tools.registry import ToolRegistry

# Baseline assistant persona used when no named system prompt is selected.
DEFAULT_SYSTEM_PROMPT = (
    "You are the assistant for Personal OS, a unified personal dashboard. "
    "Be concise, helpful, and direct. You can look up the user's emails, "
    "calendar events, and notifications, search the user's personal knowledge "
    "base of uploaded documents, fetch and scrape public web pages, and "
    "manage the user's tasks and dashboard widgets. When you answer from the "
    "knowledge base, cite the passages you used as [n]. You can also send email, "
    "create or delete calendar events, send the user a Telegram message, and "
    "fill in and submit web forms. Creating a task takes effect immediately; "
    "every other write — task updates/deletes, widget config, and all outbound "
    "actions (email, calendar, Telegram, form submission) — is proposed for the "
    "user to approve before it runs. Tell the user when you have proposed such "
    "an action and that it is awaiting their approval. Use tools when they help; "
    "otherwise answer directly. If you are unsure, say so."
)

# Safety cap on tool round-trips per turn so a misbehaving loop can't run away.
MAX_TOOL_ITERATIONS = 5
# Length of a tool result kept for UI surfacing / persistence.
_SUMMARY_CHARS = 280


class AIService(AIServiceInterface):
    """Route chat prompts to a provider, run tools, and persist the exchange."""

    def __init__(
        self,
        provider: LLMProvider,
        conversations: ConversationService,
        prompts: SystemPromptRepository,
        *,
        max_tokens: int,
        temperature: float,
        tools: ToolRegistry | None = None,
        confirmations: ConfirmationService | None = None,
    ) -> None:
        self._provider = provider
        self._conversations = conversations
        self._prompts = prompts
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._tools = tools
        self._confirmations = confirmations

    # --- Chat (non-streaming) ---------------------------------------------

    def chat(
        self,
        user_id: int,
        *,
        message: str,
        conversation_id: int | None = None,
        system_prompt_id: int | None = None,
    ) -> ChatResult | None:
        """Send a user message and return the assistant reply.

        Returns None when ``conversation_id`` is supplied but not owned by the
        user. Provider failures propagate as ``ProviderError`` for the route to
        translate into an HTTP status.
        """
        conversation = self._start_turn(user_id, conversation_id, message)
        if conversation is None:
            return None
        self._bind_confirmations(conversation.id)

        system = self._resolve_system_prompt(system_prompt_id)
        working = self._working_history(conversation.id)
        invocations: list[ToolInvocation] = []

        final = self._run_tool_loop(conversation, working, system, invocations)

        assistant_message = self._conversations.append_message(
            conversation,
            role="assistant",
            content=final.content,
            provider=final.provider,
            model=final.model,
        )
        return ChatResult(
            conversation_id=conversation.id,
            message=self._message_read(assistant_message),
            provider=final.provider,
            model=final.model,
            tool_calls=invocations,
            pending_actions=self._pending_actions(),
            metadata=final.metadata,
        )

    # --- Chat (SSE streaming) ---------------------------------------------

    def stream(
        self,
        user_id: int,
        *,
        message: str,
        conversation_id: int | None = None,
        system_prompt_id: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield streaming events for a chat turn.

        Event types: ``conversation`` (id), ``tool_call`` (a tool that ran),
        ``token`` (a text delta), ``done`` (final message metadata), ``error``.
        Tool resolution uses a non-streaming pass; the final answer is streamed
        when the provider has no tools, and delivered as chunks otherwise.
        """
        conversation = self._start_turn(user_id, conversation_id, message)
        if conversation is None:
            yield {"type": "error", "detail": "Conversation not found"}
            return
        self._bind_confirmations(conversation.id)
        yield {"type": "conversation", "conversation_id": conversation.id}

        system = self._resolve_system_prompt(system_prompt_id)
        working = self._working_history(conversation.id)
        invocations: list[ToolInvocation] = []

        try:
            prefetched = self._resolve_tools(
                conversation, working, system, invocations
            )
            for invocation in invocations:
                yield {
                    "type": "tool_call",
                    "name": invocation.name,
                    "arguments": invocation.arguments,
                    "summary": invocation.summary,
                }
            # Surface any writes proposed this turn so the UI can prompt for
            # approval as soon as the tool loop settles.
            for action in self._pending_actions():
                yield {"type": "pending_action", **action.model_dump(mode="json")}

            parts: list[str] = []
            if prefetched is not None:
                # Tools were available: stream the already-produced final text.
                for token in self._chunk(prefetched):
                    parts.append(token)
                    yield {"type": "token", "text": token}
            else:
                for token in self._provider.stream_chat(
                    working,
                    system=system,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                ):
                    parts.append(token)
                    yield {"type": "token", "text": token}
        except Exception as exc:  # noqa: BLE001 — surface provider failures as events
            yield {"type": "error", "detail": str(exc)}
            return

        assistant_message = self._conversations.append_message(
            conversation,
            role="assistant",
            content="".join(parts),
            provider=self._provider.provider,
            model=self._provider.model,
        )
        yield {
            "type": "done",
            "message_id": assistant_message.id,
            "conversation_id": conversation.id,
            "provider": self._provider.provider,
            "model": self._provider.model,
        }

    # --- Prompts & diagnostics --------------------------------------------

    def list_prompts(self) -> list[SystemPromptRead]:
        return [
            SystemPromptRead(
                id=p.id,
                name=p.name,
                description=p.description,
                system_prompt=p.system_prompt,
            )
            for p in self._prompts.list()
        ]

    def health(self) -> AIHealth:
        return AIHealth(
            provider=self._provider.provider,
            model=self._provider.model,
            available=self._provider.available(),
        )

    # --- Tool-use loop -----------------------------------------------------

    def _run_tool_loop(
        self,
        conversation: Conversation,
        working: list[ChatMessage],
        system: str,
        invocations: list[ToolInvocation],
    ):
        """Drive the tool loop and return the provider's final ChatResponse."""
        tools = self._active_tools()
        response = self._provider.chat(
            working,
            system=system,
            tools=tools,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )
        iterations = 0
        while response.tool_calls and tools and iterations < MAX_TOOL_ITERATIONS:
            self._apply_tool_calls(conversation, working, response.tool_calls, invocations)
            iterations += 1
            response = self._provider.chat(
                working,
                system=system,
                tools=tools,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
        return response

    def _resolve_tools(
        self,
        conversation: Conversation,
        working: list[ChatMessage],
        system: str,
        invocations: list[ToolInvocation],
    ) -> str | None:
        """Run the tool loop for the streaming path.

        Returns the final answer text when a non-streaming pass was used (tools
        available), or None to signal the caller should stream directly.
        """
        if not self._active_tools():
            return None
        return self._run_tool_loop(conversation, working, system, invocations).content

    def _apply_tool_calls(
        self,
        conversation: Conversation,
        working: list[ChatMessage],
        tool_calls: list[ToolCall],
        invocations: list[ToolInvocation],
    ) -> None:
        """Record the assistant's tool request, run each tool, feed results back."""
        working.append(
            ChatMessage(role="assistant", content="", tool_calls=tool_calls)
        )
        for call in tool_calls:
            result = self._tools.execute(call.name, call.arguments)
            summary = self._summarize(result)
            invocations.append(
                ToolInvocation(
                    name=call.name, arguments=call.arguments, summary=summary
                )
            )
            # Persist a compact tool step so reopening the thread shows sources.
            self._conversations.append_message(
                conversation, role="tool", content=f"{call.name}: {summary}"
            )
            working.append(
                ChatMessage(
                    role="tool",
                    content=result,
                    tool_call_id=call.id,
                    name=call.name,
                )
            )

    def _active_tools(self):
        """Tool specs to advertise, or None when tools are unavailable."""
        if self._tools and self._provider.supports_tools:
            return self._tools.specs()
        return None

    # --- Confirmation flow -------------------------------------------------

    def _bind_confirmations(self, conversation_id: int) -> None:
        """Attach this turn's proposed write actions to the conversation."""
        if self._confirmations is not None:
            self._confirmations.bind_conversation(conversation_id)

    def _pending_actions(self) -> list[PendingActionRead]:
        """Pending actions proposed during the current turn (may be empty)."""
        if self._confirmations is None:
            return []
        return self._confirmations.created_this_turn()

    # --- Internals ---------------------------------------------------------

    def _start_turn(
        self, user_id: int, conversation_id: int | None, message: str
    ) -> Conversation | None:
        conversation = self._conversations.ensure_conversation(
            user_id, conversation_id, first_message=message
        )
        if conversation is None:
            return None
        self._conversations.append_message(
            conversation, role="user", content=message
        )
        return conversation

    def _working_history(self, conversation_id: int) -> list[ChatMessage]:
        """Provider-facing history: persisted user/assistant text turns only.

        Tool steps are persisted for the UI but rebuilt in-memory during the
        loop, so they are excluded here.
        """
        return [
            ChatMessage(role=m.role, content=m.content)
            for m in self._conversations.history(conversation_id)
            if m.role in ("user", "assistant")
        ]

    def _resolve_system_prompt(self, system_prompt_id: int | None) -> str:
        if system_prompt_id is None:
            return DEFAULT_SYSTEM_PROMPT
        prompt = self._prompts.get(system_prompt_id)
        return prompt.system_prompt if prompt else DEFAULT_SYSTEM_PROMPT

    @staticmethod
    def _summarize(result: str) -> str:
        text = " ".join(result.split())
        return text if len(text) <= _SUMMARY_CHARS else text[:_SUMMARY_CHARS] + "…"

    @staticmethod
    def _chunk(text: str) -> Iterator[str]:
        """Split a finished answer into word-sized tokens for incremental UI."""
        for word in text.split(" "):
            yield word + " "

    @staticmethod
    def _message_read(row) -> MessageRead:
        return MessageRead(
            id=row.id,
            conversation_id=row.conversation_id,
            role=row.role,
            content=row.content,
            provider=row.provider,
            model=row.model,
            created_at=row.created_at,
        )
