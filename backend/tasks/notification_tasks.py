"""Scheduled job callables.

Thin orchestration only: open a session, build services via the factory, and
invoke service methods. No notification logic lives here (per ARCHITECTURE) —
composition, formatting, and delivery are the service layer's concern. Each job
is best-effort so a single failure never tears down the scheduler.
"""

import logging

from sqlmodel import Session

from backend.config import Settings
from backend.database import engine
from backend.repositories.account_repository import AccountRepository
from backend.services.factory import (
    build_notification_service,
    build_sync_service,
    owner_user_id,
)

logger = logging.getLogger(__name__)


def poll_and_deliver(settings: Settings) -> None:
    """Refresh synced data (best-effort), compose notifications, and deliver."""
    with Session(engine) as session:
        user_id = owner_user_id(session)
        if user_id is None:
            return
        _refresh_synced_data(session, settings, user_id)
        service = build_notification_service(session, settings)
        service.compose_and_deliver(user_id)


def send_daily_summary(settings: Settings) -> None:
    """Compose and deliver the once-per-day activity summary."""
    with Session(engine) as session:
        user_id = owner_user_id(session)
        if user_id is None:
            return
        build_notification_service(session, settings).daily_summary(user_id)


def _refresh_synced_data(session: Session, settings: Settings, user_id: int) -> None:
    sync = build_sync_service(session, settings)
    if sync is None:
        return
    for account in AccountRepository(session).list_for_user(user_id):
        try:
            sync.sync_account(account.id)
        except Exception:  # noqa: BLE001 — best-effort; failures land in SyncState
            logger.exception("Scheduled sync failed for account %s", account.id)
