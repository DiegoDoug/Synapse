"""Notification data access. No business logic."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from backend.models.notification import Notification


class NotificationRepository:
    """Queries and transactions for in-app notifications."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, notification_id: int) -> Notification | None:
        return self._session.get(Notification, notification_id)

    def get_by_source_key(self, user_id: int, source_key: str) -> Notification | None:
        statement = select(Notification).where(
            Notification.user_id == user_id,
            Notification.source_key == source_key,
        )
        return self._session.exec(statement).first()

    def list_for_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.is_read == False)  # noqa: E712
        statement = (
            statement.order_by(Notification.created_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def list_undelivered(self, user_id: int, *, limit: int = 50) -> list[Notification]:
        statement = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_delivered == False,  # noqa: E712
            )
            .order_by(Notification.created_at.asc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def count(self, user_id: int, *, unread_only: bool = False) -> int:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.is_read == False)  # noqa: E712
        return len(list(self._session.exec(statement).all()))

    def add(self, notification: Notification) -> Notification:
        self._session.add(notification)
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def update(self, notification: Notification) -> Notification:
        self._session.add(notification)
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def mark_all_read(self, user_id: int) -> int:
        statement = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        rows = list(self._session.exec(statement).all())
        now = datetime.now(UTC)
        for row in rows:
            row.is_read = True
            row.read_at = now
            self._session.add(row)
        self._session.commit()
        return len(rows)
