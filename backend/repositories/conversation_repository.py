"""Conversation + message data access. No business logic."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from backend.models.conversation import Conversation
from backend.models.message import Message


class ConversationRepository:
    """Queries and transactions for conversations and their messages."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Conversations -----------------------------------------------------

    def get(self, conversation_id: int) -> Conversation | None:
        return self._session.get(Conversation, conversation_id)

    def list_for_user(
        self, user_id: int, *, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def add(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        self._session.commit()
        self._session.refresh(conversation)
        return conversation

    def touch(self, conversation: Conversation) -> Conversation:
        """Bump ``updated_at`` so recent threads sort first."""
        conversation.updated_at = datetime.now(UTC)
        self._session.add(conversation)
        self._session.commit()
        self._session.refresh(conversation)
        return conversation

    # --- Messages ----------------------------------------------------------

    def list_messages(self, conversation_id: int) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())  # type: ignore[union-attr]
        )
        return list(self._session.exec(statement).all())

    def add_message(self, message: Message) -> Message:
        self._session.add(message)
        self._session.commit()
        self._session.refresh(message)
        return message
