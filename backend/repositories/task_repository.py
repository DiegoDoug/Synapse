"""Task data access. No business logic."""

from sqlmodel import Session, select

from backend.models.task import Task


class TaskRepository:
    """Queries and transactions for personal tasks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, task_id: int) -> Task | None:
        return self._session.get(Task, task_id)

    def list_for_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Task]:
        statement = select(Task).where(Task.user_id == user_id)
        if status is not None:
            statement = statement.where(Task.status == status)
        statement = (
            statement.order_by(Task.created_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def add(self, task: Task) -> Task:
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return task

    def update(self, task: Task) -> Task:
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self._session.delete(task)
        self._session.commit()
