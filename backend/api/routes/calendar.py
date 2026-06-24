"""Calendar routes — read synced Google Calendar events and trigger sync.

Endpoints (under /api/v1):
- GET  /accounts/{account_id}/events            list synced events
- GET  /accounts/{account_id}/events/{event_id} get one synced event
- POST /accounts/{account_id}/events/sync       run an incremental sync
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_calendar_service
from backend.schemas.calendar import EventDetail, EventSummary
from backend.schemas.sync import SyncResult
from backend.services.calendar_service import CalendarService

router = APIRouter(prefix="/accounts/{account_id}/events", tags=["calendar"])


@router.get("", response_model=list[EventSummary])
def list_events(
    account_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CalendarService = Depends(get_calendar_service),
) -> list[EventSummary]:
    return service.list_events(account_id, limit=limit, offset=offset)


@router.post("/sync", response_model=SyncResult)
def sync_events(
    account_id: int,
    service: CalendarService = Depends(get_calendar_service),
) -> SyncResult:
    return service.sync(account_id)


@router.get("/{event_id}", response_model=EventDetail)
def get_event(
    account_id: int,
    event_id: int,
    service: CalendarService = Depends(get_calendar_service),
) -> EventDetail:
    event = service.get_event(account_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
