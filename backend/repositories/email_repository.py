"""EmailMessage data access. No business logic."""

from sqlalchemy import func
from sqlmodel import Session, select

from backend.models.email_message import EmailMessage


class EmailRepository:
    """Queries and transactions for synced email messages."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, message_id: int) -> EmailMessage | None:
        return self._session.get(EmailMessage, message_id)

    def get_by_external_id(self, account_id: int, external_id: str) -> EmailMessage | None:
        statement = select(EmailMessage).where(
            EmailMessage.account_id == account_id,
            EmailMessage.external_id == external_id,
        )
        return self._session.exec(statement).first()

    def list_for_account(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[EmailMessage]:
        statement = select(EmailMessage).where(EmailMessage.account_id == account_id)
        if unread_only:
            statement = statement.where(EmailMessage.is_read == False)  # noqa: E712
        statement = (
            statement.order_by(EmailMessage.received_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def max_id_for_accounts(self, account_ids: list[int]) -> int:
        """Highest synced message id across the given accounts (0 if none).

        A monotonic high-water mark for event triggers — read only, against
        already-synced rows.
        """
        if not account_ids:
            return 0
        statement = select(func.max(EmailMessage.id)).where(
            EmailMessage.account_id.in_(account_ids)  # type: ignore[attr-defined]
        )
        return self._session.exec(statement).one() or 0

    def upsert(self, message: EmailMessage) -> EmailMessage:
        self._session.add(message)
        self._session.commit()
        self._session.refresh(message)
        return message
