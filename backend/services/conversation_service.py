"""Conversation service — persistence and reads for AI chat threads.

Owns the conversation/message lifecycle on behalf of ``AIService`` and the
conversation routes: creating threads, appending turns, and returning read
views. All access is scoped to the owning user. No provider calls happen here.
"""

from __future__ import annotations

from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.repositories.conversation_repository import ConversationRepository
from backend.schemas.ai import (
    ConversationDetail,
    ConversationRead,
    MessageRead,
)
from backend.services.interfaces import ConversationServiceInterface

# Derive a thread title from its first user message when none was supplied.
_TITLE_MAX = 60


class ConversationService(ConversationServiceInterface):
    """Create, read, and append to AI conversations."""

    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    # --- Reads -------------------------------------------------------------

    def list(
        self, user_id: int, *, limit: int = 50, offset: int = 0
    ) -> list[ConversationRead]:
        rows = self._conversations.list_for_user(user_id, limit=limit, offset=offset)
        return [self._to_read(row) for row in rows]

    def get(self, user_id: int, conversation_id: int) -> ConversationDetail | None:
        row = self._owned(user_id, conversation_id)
        if row is None:
            return None
        messages = self._conversations.list_messages(conversation_id)
        return ConversationDetail(
            **self._to_read(row).model_dump(),
            messages=[self._message_read(m) for m in messages],
        )

    # --- Writes ------------------------------------------------------------

    def create(self, user_id: int, *, title: str | None = None) -> ConversationRead:
        conversation = Conversation(
            user_id=user_id, title=title or "New conversation"
        )
        return self._to_read(self._conversations.add(conversation))

    def ensure_conversation(
        self, user_id: int, conversation_id: int | None, *, first_message: str
    ) -> Conversation | None:
        """Return an owned conversation, creating one titled from the first
        message when ``conversation_id`` is None. None means the id was supplied
        but does not belong to the user."""
        if conversation_id is None:
            conversation = Conversation(
                user_id=user_id, title=self._derive_title(first_message)
            )
            return self._conversations.add(conversation)
        return self._owned(user_id, conversation_id)

    def append_message(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> Message:
        """Persist a message and bump the conversation's recency."""
        message = self._conversations.add_message(
            Message(
                conversation_id=conversation.id,
                role=role,
                content=content,
                provider=provider,
                model=model,
            )
        )
        self._conversations.touch(conversation)
        return message

    def history(self, conversation_id: int) -> list[Message]:
        """Ordered messages for a conversation (for prompt assembly)."""
        return self._conversations.list_messages(conversation_id)

    # --- Internals ---------------------------------------------------------

    def _owned(self, user_id: int, conversation_id: int) -> Conversation | None:
        row = self._conversations.get(conversation_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    @staticmethod
    def _derive_title(message: str) -> str:
        text = " ".join(message.strip().split())
        if len(text) <= _TITLE_MAX:
            return text or "New conversation"
        return f"{text[:_TITLE_MAX].rstrip()}…"

    @staticmethod
    def _to_read(row: Conversation) -> ConversationRead:
        return ConversationRead(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _message_read(row: Message) -> MessageRead:
        return MessageRead(
            id=row.id,
            conversation_id=row.conversation_id,
            role=row.role,
            content=row.content,
            provider=row.provider,
            model=row.model,
            created_at=row.created_at,
        )
