"""Connection routes — Google account OAuth + connection management.

Endpoints (under /api/v1):
- GET    /connections                  list connected accounts
- GET    /connections/google/authorize get the consent-screen URL
- GET    /connections/google/callback  OAuth redirect target (token exchange)
- DELETE /connections/{account_id}      disconnect an account
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_connection_service, get_current_user_id
from backend.schemas.connection import AuthorizationUrlResponse, ConnectionRead
from backend.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionRead])
def list_connections(
    service: ConnectionService = Depends(get_connection_service),
    user_id: int = Depends(get_current_user_id),
) -> list[ConnectionRead]:
    return service.list_connections(user_id)


@router.get("/google/authorize", response_model=AuthorizationUrlResponse)
def authorize_google(
    service: ConnectionService = Depends(get_connection_service),
    user_id: int = Depends(get_current_user_id),
) -> AuthorizationUrlResponse:
    return service.build_authorization_url(user_id)


@router.get("/google/callback", response_model=ConnectionRead)
def google_callback(
    code: str,
    state: str = "",
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionRead:
    return service.complete_authorization(code, state)


@router.delete("/{account_id}", status_code=204)
def disconnect(
    account_id: int,
    service: ConnectionService = Depends(get_connection_service),
) -> None:
    try:
        service.disconnect(account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
