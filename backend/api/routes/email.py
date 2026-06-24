"""Email routes — read synced Gmail messages and trigger sync.

Endpoints (under /api/v1):
- GET  /accounts/{account_id}/emails              list synced messages
- GET  /accounts/{account_id}/emails/{message_id} get one synced message
- POST /accounts/{account_id}/emails/sync         run an incremental sync
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_email_service
from backend.schemas.email import EmailDetail, EmailSummary
from backend.schemas.sync import SyncResult
from backend.services.email_service import EmailService

router = APIRouter(prefix="/accounts/{account_id}/emails", tags=["email"])


@router.get("", response_model=list[EmailSummary])
def list_emails(
    account_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = False,
    service: EmailService = Depends(get_email_service),
) -> list[EmailSummary]:
    return service.list_messages(
        account_id, limit=limit, offset=offset, unread_only=unread_only
    )


@router.post("/sync", response_model=SyncResult)
def sync_emails(
    account_id: int,
    service: EmailService = Depends(get_email_service),
) -> SyncResult:
    return service.sync(account_id)


@router.get("/{message_id}", response_model=EmailDetail)
def get_email(
    account_id: int,
    message_id: int,
    service: EmailService = Depends(get_email_service),
) -> EmailDetail:
    message = service.get_message(account_id, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message
