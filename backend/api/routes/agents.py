"""Agent routes — the Stage 6 agent layer.

Endpoints (under /api/v1):
- GET  /agents                 list the runnable agents (catalogue)
- GET  /agents/runs            list recent runs (history, newest first)
- GET  /agents/runs/{id}       fetch one run with its plan→act→observe steps
- POST /agents/{key}/runs      start an agent run and return the recorded run

Starting a run executes the agent synchronously through the service layer and
returns the completed run (status, result, and every step). All reads are scoped
to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_agent_service, get_current_user_id
from backend.schemas.agent import (
    AgentInfo,
    AgentRunRead,
    AgentRunSummary,
    StartRunRequest,
)
from backend.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
def list_agents(
    service: AgentService = Depends(get_agent_service),
) -> list[AgentInfo]:
    return service.list_agents()


@router.get("/runs", response_model=list[AgentRunSummary])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    user_id: int = Depends(get_current_user_id),
    service: AgentService = Depends(get_agent_service),
) -> list[AgentRunSummary]:
    return service.list_runs(user_id, limit=limit)


@router.get("/runs/{run_id}", response_model=AgentRunRead)
def get_run(
    run_id: int,
    user_id: int = Depends(get_current_user_id),
    service: AgentService = Depends(get_agent_service),
) -> AgentRunRead:
    run = service.get_run(user_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{agent_key}/runs", response_model=AgentRunRead)
def start_run(
    agent_key: str,
    request: StartRunRequest,
    user_id: int = Depends(get_current_user_id),
    service: AgentService = Depends(get_agent_service),
) -> AgentRunRead:
    run = service.start(user_id, agent_key, request.params)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_key}'")
    return run
