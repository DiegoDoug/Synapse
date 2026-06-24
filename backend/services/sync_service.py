"""Sync service — coordinate synchronization across an account's resources.

Orchestrates the per-resource services (email, calendar) and reports the
current sync checkpoint for each resource. Holds no provider HTTP logic itself.
"""

from backend.repositories.sync_state_repository import SyncStateRepository
from backend.schemas.sync import SyncResult, SyncStatusRead
from backend.services.calendar_service import CalendarService
from backend.services.email_service import EmailService
from backend.services.interfaces import SyncServiceInterface


class SyncService(SyncServiceInterface):
    """Run and report synchronization across all resources of an account."""

    def __init__(
        self,
        email: EmailService,
        calendar: CalendarService,
        sync_states: SyncStateRepository,
    ) -> None:
        self._email = email
        self._calendar = calendar
        self._sync_states = sync_states

    def sync_account(self, account_id: int) -> list[SyncResult]:
        return [
            self._email.sync(account_id),
            self._calendar.sync(account_id),
        ]

    def get_status(self, account_id: int) -> list[SyncStatusRead]:
        states = self._sync_states.list_for_account(account_id)
        return [
            SyncStatusRead(
                account_id=state.account_id,
                resource=state.resource,
                status=state.status,
                last_synced_at=state.last_synced_at,
                error=state.error,
            )
            for state in states
        ]
