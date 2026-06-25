"""Action routes — the confirmation flow for assistant-proposed writes.

Endpoints (under /api/v1):
- GET  /actions                 list proposed actions (newest first)
- GET  /actions/{id}            fetch one proposed action
- POST /actions/{id}/approve    approve and execute a pending action
- POST /actions/{id}/reject     reject a pending action without running it

Updates and deletes proposed by the assistant land here as ``pending`` actions;
the user approves (executing them through the service layer) or rejects them.
All endpoints are scoped to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_confirmation_service, get_current_user_id
from backend.schemas.action import PendingActionRead
from backend.services.confirmation_service import ConfirmationService

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=list[PendingActionRead])
def list_actions(
    pending_only: bool = Query(False),
    user_id: int = Depends(get_current_user_id),
    service: ConfirmationService = Depends(get_confirmation_service),
) -> list[PendingActionRead]:
    return service.list(user_id, pending_only=pending_only)


@router.get("/{action_id}", response_model=PendingActionRead)
def get_action(
    action_id: int,
    user_id: int = Depends(get_current_user_id),
    service: ConfirmationService = Depends(get_confirmation_service),
) -> PendingActionRead:
    action = service.get(user_id, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/approve", response_model=PendingActionRead)
def approve_action(
    action_id: int,
    user_id: int = Depends(get_current_user_id),
    service: ConfirmationService = Depends(get_confirmation_service),
) -> PendingActionRead:
    action = service.approve(user_id, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/reject", response_model=PendingActionRead)
def reject_action(
    action_id: int,
    user_id: int = Depends(get_current_user_id),
    service: ConfirmationService = Depends(get_confirmation_service),
) -> PendingActionRead:
    action = service.reject(user_id, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action
