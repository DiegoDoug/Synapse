"""Task routes — the personal to-do list.

Endpoints (under /api/v1):
- GET    /tasks            list tasks (newest first; optional status filter)
- POST   /tasks           create a task
- GET    /tasks/{id}       fetch one task
- PATCH  /tasks/{id}       update a task
- DELETE /tasks/{id}       delete a task

These power the UI and let the user review the tasks the assistant proposes and
creates. All endpoints are scoped to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user_id, get_task_service
from backend.schemas.task import TaskCreate, TaskRead, TaskUpdate
from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    user_id: int = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
) -> list[TaskRead]:
    return service.list(user_id, limit=limit, offset=offset, status=status)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    user_id: int = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    return service.create(user_id, payload)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    task = service.get(user_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user_id: int = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    task = service.update(user_id, task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
) -> None:
    if not service.delete(user_id, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
