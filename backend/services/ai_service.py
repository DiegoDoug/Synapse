"""AI service — provider routing, prompt assembly, and chat orchestration.

The single entry point for AI chat. It selects the active provider (injected),
assembles the system prompt + conversation history, calls the provider, and
persists both the user turn and the assistant reply via ``ConversationService``.

Providers are never imported by routes — only this service talks to them, and
only through the ``LLMProvider`` interface, which keeps them swappable. No
agent logic, tools, or memory live here (those are later stages).
"""

from __future__ import annotations

from backend.integrations.ai.base import LLMProvider
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.schemas.ai import (
    AIHealth,
    ChatMessage,
    ChatResult,
    MessageRead,
    SystemPromptRead,
)
from backend.services.conversation_service import ConversationService
from backend.services.interfaces import AIServiceInterface

# Baseline assistant persona used when no named system prompt is selected.
DEFAULT_SYSTEM_PROMPT = (
    "You are the assistant for Personal OS, a unified personal dashboard. "
    "Be concise, helpful, and direct. If you are unsure, say so."
)


class AIService(AIServiceInterface):
    """Route chat prompts to a provider and persist the conversation."""

    def __init__(
        self,
        provider: LLMProvider,
        conversations: ConversationService,
        prompts: SystemPromptRepository,
        *,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self._provider = provider
        self._conversations = conversations
        self._prompts = prompts
        self._max_tokens = max_tokens
        self._temperature = temperature

    # --- Chat --------------------------------------------------------------

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
        conversation = self._conversations.ensure_conversation(
            user_id, conversation_id, first_message=message
        )
        if conversation is None:
            return None

        self._conversations.append_message(
            conversation, role="user", content=message
        )

        system = self._resolve_system_prompt(system_prompt_id)
        history = [
            ChatMessage(role=m.role, content=m.content)
            for m in self._conversations.history(conversation.id)
            if m.role in ("user", "assistant")
        ]

        response = self._provider.chat(
            history,
            system=system,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

        assistant_message = self._conversations.append_message(
            conversation,
            role="assistant",
            content=response.content,
            provider=response.provider,
            model=response.model,
        )

        return ChatResult(
            conversation_id=conversation.id,
            message=MessageRead(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                role=assistant_message.role,
                content=assistant_message.content,
                provider=assistant_message.provider,
                model=assistant_message.model,
                created_at=assistant_message.created_at,
            ),
            provider=response.provider,
            model=response.model,
            metadata=response.metadata,
        )

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

    # --- Internals ---------------------------------------------------------

    def _resolve_system_prompt(self, system_prompt_id: int | None) -> str:
        if system_prompt_id is None:
            return DEFAULT_SYSTEM_PROMPT
        prompt = self._prompts.get(system_prompt_id)
        return prompt.system_prompt if prompt else DEFAULT_SYSTEM_PROMPT
