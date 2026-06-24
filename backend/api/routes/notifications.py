"""Notification routes — the in-app notification center.

Endpoints (under /api/v1):
- GET  /notifications                 list notifications (newest first)
- GET  /notifications/counts          unread/total counts (badge)
- GET  /notifications/telegram        Telegram delivery status
- POST /notifications                 create a manual notification
- POST /notifications/compose         compose notifications from synced data
- POST /notifications/deliver         deliver undelivered notifications to Telegram
- POST /notifications/{id}/read       mark one notification read
- POST /notifications/{id}/send       deliver one notification to Telegram
- POST /notifications/read-all        mark every notification read

All endpoints are scoped to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user_id, get_notification_service
from backend.schemas.notification import (
    ComposeResult,
    DeliveryResult,
    MarkAllReadResult,
    NotificationCounts,
    NotificationCreate,
    NotificationRead,
    TelegramStatus,
)
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = False,
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationRead]:
    return service.list(
        user_id, limit=limit, offset=offset, unread_only=unread_only
    )


@router.get("/counts", response_model=NotificationCounts)
def notification_counts(
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationCounts:
    return service.counts(user_id)


@router.post("", response_model=NotificationRead, status_code=201)
def create_notification(
    payload: NotificationCreate,
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRead:
    return service.create(user_id, payload)


@router.post("/compose", response_model=ComposeResult)
def compose_notifications(
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> ComposeResult:
    return service.compose(user_id)


@router.get("/telegram", response_model=TelegramStatus)
def telegram_status(
    service: NotificationService = Depends(get_notification_service),
) -> TelegramStatus:
    return service.telegram_status()


@router.post("/deliver", response_model=DeliveryResult)
def deliver_pending(
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> DeliveryResult:
    return service.deliver_pending(user_id)


@router.post("/{notification_id}/send", response_model=DeliveryResult)
def send_notification(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> DeliveryResult:
    result = service.send(user_id, notification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.post("/read-all", response_model=MarkAllReadResult)
def mark_all_read(
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> MarkAllReadResult:
    return MarkAllReadResult(updated=service.mark_all_read(user_id))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRead:
    notification = service.mark_read(user_id, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
