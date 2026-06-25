"""Task service — business logic for personal tasks.

Owns the task lifecycle on behalf of the tasks routes and the ``ToolExecutor``
(which runs assistant-proposed task writes). All access is scoped to the owning
user; the service talks only to ``TaskRepository``, never to the session.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.models.task import Task
from backend.repositories.task_repository import TaskRepository
from backend.schemas.task import TaskCreate, TaskRead, TaskUpdate


class TaskService:
    """Create, read, update, and delete personal tasks."""

    def __init__(self, tasks: TaskRepository) -> None:
        self._tasks = tasks

    # --- Reads -------------------------------------------------------------

    def list(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[TaskRead]:
        rows = self._tasks.list_for_user(
            user_id, limit=limit, offset=offset, status=status
        )
        return [self._to_read(row) for row in rows]

    def get(self, user_id: int, task_id: int) -> TaskRead | None:
        row = self._owned(user_id, task_id)
        return self._to_read(row) if row else None

    # --- Writes ------------------------------------------------------------

    def create(self, user_id: int, payload: TaskCreate) -> TaskRead:
        task = Task(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            due_at=payload.due_at,
        )
        return self._to_read(self._tasks.add(task))

    def update(
        self, user_id: int, task_id: int, payload: TaskUpdate
    ) -> TaskRead | None:
        """Apply the supplied fields. Returns None if not owned/found."""
        task = self._owned(user_id, task_id)
        if task is None:
            return None

        fields = payload.model_dump(exclude_unset=True)
        for key, value in fields.items():
            setattr(task, key, value)

        # Stamp completion when the status flips to/from done.
        if "status" in fields:
            task.completed_at = (
                datetime.now(UTC) if task.status == "done" else None
            )
        task.updated_at = datetime.now(UTC)
        return self._to_read(self._tasks.update(task))

    def delete(self, user_id: int, task_id: int) -> bool:
        """Delete a task. Returns False if not owned/found."""
        task = self._owned(user_id, task_id)
        if task is None:
            return False
        self._tasks.delete(task)
        return True

    # --- Internals ---------------------------------------------------------

    def _owned(self, user_id: int, task_id: int) -> Task | None:
        row = self._tasks.get(task_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    @staticmethod
    def _to_read(row: Task) -> TaskRead:
        return TaskRead(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            description=row.description,
            status=row.status,
            priority=row.priority,
            due_at=row.due_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
