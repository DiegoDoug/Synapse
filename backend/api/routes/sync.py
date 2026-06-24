"""Sync routes — run and inspect synchronization for an account.

Endpoints (under /api/v1):
- POST /accounts/{account_id}/sync         sync all resources (email + calendar)
- GET  /accounts/{account_id}/sync/status  current checkpoint per resource
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_sync_service
from backend.schemas.sync import SyncResult, SyncStatusRead
from backend.services.sync_service import SyncService

router = APIRouter(prefix="/accounts/{account_id}/sync", tags=["sync"])


@router.post("", response_model=list[SyncResult])
def sync_account(
    account_id: int,
    service: SyncService = Depends(get_sync_service),
) -> list[SyncResult]:
    return service.sync_account(account_id)


@router.get("/status", response_model=list[SyncStatusRead])
def sync_status(
    account_id: int,
    service: SyncService = Depends(get_sync_service),
) -> list[SyncStatusRead]:
    return service.get_status(account_id)
