"""Workflow routes — the Stage 7 automation layer.

Endpoints (under /api/v1):
- GET    /workflows                 list the user's workflows
- POST   /workflows                 define a new workflow
- GET    /workflows/{id}            read one workflow
- PATCH  /workflows/{id}            update a definition / schedule
- DELETE /workflows/{id}            delete a workflow (and its run history)
- POST   /workflows/{id}/enable     enable the schedule
- POST   /workflows/{id}/disable    disable the schedule
- POST   /workflows/{id}/run        run the workflow on demand now
- GET    /workflows/{id}/runs       read the workflow's run history

Defining/updating a workflow personalizes when and how often it runs (interval
or a daily time) and how many times before it auto-disables. Running a workflow
hands off to the Stage 6 agent layer and records the outcome. All reads are
scoped to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user_id, get_workflow_service
from backend.schemas.workflow import (
    WorkflowCatalogue,
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunRead,
    WorkflowUpdate,
)
from backend.services.workflow_service import WorkflowError, WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowRead])
def list_workflows(
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowRead]:
    return service.list_workflows(user_id)


@router.post("", response_model=WorkflowRead, status_code=201)
def create_workflow(
    body: WorkflowCreate,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    try:
        return service.create_workflow(user_id, body)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/catalogue", response_model=WorkflowCatalogue)
def get_catalogue(
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowCatalogue:
    """The agents, tools, and events the composer can build steps from."""
    return service.catalogue()


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    workflow = service.get_workflow(user_id, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
    workflow_id: int,
    body: WorkflowUpdate,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    try:
        workflow = service.update_workflow(user_id, workflow_id, body)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(
    workflow_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> None:
    if not service.delete_workflow(user_id, workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/enable", response_model=WorkflowRead)
def enable_workflow(
    workflow_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    return _set_enabled(service, user_id, workflow_id, True)


@router.post("/{workflow_id}/disable", response_model=WorkflowRead)
def disable_workflow(
    workflow_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    return _set_enabled(service, user_id, workflow_id, False)


@router.post("/{workflow_id}/run", response_model=WorkflowRunRead)
def run_workflow(
    workflow_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRunRead:
    run = service.run_now(user_id, workflow_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return run


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunRead])
def list_workflow_runs(
    workflow_id: int,
    limit: int = Query(50, ge=1, le=200),
    user_id: int = Depends(get_current_user_id),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowRunRead]:
    runs = service.list_runs(user_id, workflow_id, limit=limit)
    if runs is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return runs


def _set_enabled(
    service: WorkflowService, user_id: int, workflow_id: int, enabled: bool
) -> WorkflowRead:
    try:
        workflow = service.set_enabled(user_id, workflow_id, enabled)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow
