"""PendingAction data access. No business logic."""

from sqlmodel import Session, select

from backend.models.pending_action import STATUS_PENDING, PendingAction


class PendingActionRepository:
    """Queries and transactions for proposed (pending) actions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, action_id: int) -> PendingAction | None:
        return self._session.get(PendingAction, action_id)

    def list_for_user(
        self,
        user_id: int,
        *,
        pending_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PendingAction]:
        statement = select(PendingAction).where(PendingAction.user_id == user_id)
        if pending_only:
            statement = statement.where(PendingAction.status == STATUS_PENDING)
        statement = (
            statement.order_by(PendingAction.created_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def add(self, action: PendingAction) -> PendingAction:
        self._session.add(action)
        self._session.commit()
        self._session.refresh(action)
        return action

    def update(self, action: PendingAction) -> PendingAction:
        self._session.add(action)
        self._session.commit()
        self._session.refresh(action)
        return action
