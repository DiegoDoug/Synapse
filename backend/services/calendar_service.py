"""Calendar service — read access and incremental Google Calendar sync.

Business logic for events: maps raw Calendar payloads to CalendarEvent rows,
performs incremental sync using a per-account syncToken cursor (full-resync
fallback on 410 Gone), and exposes synced events as DTOs.
"""

from datetime import UTC, datetime

from googleapiclient.errors import HttpError

from backend.integrations.google.calendar import GoogleCalendarIntegration
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.models.account import Account
from backend.models.calendar_event import CalendarEvent
from backend.models.sync_state import SyncState
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.schemas.calendar import EventDetail, EventSummary
from backend.schemas.sync import SyncResult
from backend.services.interfaces import CalendarServiceInterface

_RESOURCE = "calendar"
_CALENDAR_ID = "primary"


class CalendarService(CalendarServiceInterface):
    """Read synced events and run incremental Google Calendar sync."""

    def __init__(
        self,
        accounts: AccountRepository,
        events: CalendarRepository,
        sync_states: SyncStateRepository,
        oauth: GoogleOAuthClient,
    ) -> None:
        self._accounts = accounts
        self._events = events
        self._sync_states = sync_states
        self._oauth = oauth

    # --- Reads -------------------------------------------------------------

    def list_events(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EventSummary]:
        rows = self._events.list_for_account(account_id, limit=limit, offset=offset)
        return [self._to_summary(row) for row in rows]

    def get_event(self, account_id: int, event_id: int) -> EventDetail | None:
        row = self._events.get(event_id)
        if row is None or row.account_id != account_id:
            return None
        return self._to_detail(row)

    # --- Sync --------------------------------------------------------------

    def sync(self, account_id: int) -> SyncResult:
        account = self._accounts.get(account_id)
        if account is None:
            return SyncResult(
                account_id=account_id,
                resource=_RESOURCE,
                status="error",
                error="account not found",
            )

        state = self._sync_states.get(account_id, _RESOURCE) or SyncState(
            account_id=account_id, resource=_RESOURCE
        )
        state.status = "syncing"
        state.error = None
        self._sync_states.upsert(state)

        try:
            calendar = self._build_calendar(account)
            raw_events, new_cursor = self._collect_events(calendar, state.cursor)

            created = updated = 0
            for raw in raw_events:
                if self._upsert_event(account_id, raw):
                    created += 1
                else:
                    updated += 1

            self._persist_credentials(account)
            state.cursor = new_cursor
            state.status = "idle"
            state.last_synced_at = datetime.now(UTC)
            state.updated_at = datetime.now(UTC)
            self._sync_states.upsert(state)

            return SyncResult(
                account_id=account_id,
                resource=_RESOURCE,
                created=created,
                updated=updated,
                total=created + updated,
                status="ok",
            )
        except Exception as exc:  # noqa: BLE001 — surface any sync failure as state
            return self._fail(state, account_id, str(exc))

    # --- Internals ---------------------------------------------------------

    def _build_calendar(self, account: Account) -> GoogleCalendarIntegration:
        credentials = self._oauth.credentials_from_tokens(
            account.access_token,
            account.refresh_token,
            account.token_expiry,
            account.scopes.split() if account.scopes else [],
        )
        if credentials.expired and credentials.refresh_token:
            self._oauth.refresh(credentials)
        self._pending_credentials = credentials
        return GoogleCalendarIntegration(credentials)

    def _collect_events(
        self, calendar: GoogleCalendarIntegration, cursor: str | None
    ) -> tuple[list[dict], str | None]:
        if cursor:
            try:
                return calendar.list_events(_CALENDAR_ID, sync_token=cursor)
            except HttpError as exc:
                # 410 Gone => syncToken expired; fall back to a full resync.
                if exc.resp.status != 410:
                    raise
        return calendar.list_events(_CALENDAR_ID, sync_token=None)

    def _upsert_event(self, account_id: int, raw: dict) -> bool:
        """Insert or update an event. Returns True if newly created."""
        mapped = self._to_model(account_id, raw)
        existing = self._events.get_by_external_id(account_id, mapped.external_id)
        if existing is None:
            self._events.upsert(mapped)
            return True
        existing.summary = mapped.summary
        existing.description = mapped.description
        existing.location = mapped.location
        existing.status = mapped.status
        existing.all_day = mapped.all_day
        existing.start = mapped.start
        existing.end = mapped.end
        self._events.upsert(existing)
        return False

    def _persist_credentials(self, account: Account) -> None:
        credentials = getattr(self, "_pending_credentials", None)
        if credentials is None:
            return
        account.access_token = credentials.token
        account.token_expiry = credentials.expiry
        account.updated_at = datetime.now(UTC)
        self._accounts.update(account)

    def _fail(self, state: SyncState, account_id: int, error: str) -> SyncResult:
        state.status = "error"
        state.error = error
        state.updated_at = datetime.now(UTC)
        self._sync_states.upsert(state)
        return SyncResult(
            account_id=account_id, resource=_RESOURCE, status="error", error=error
        )

    @staticmethod
    def _parse_endpoint(node: dict | None) -> tuple[datetime | None, bool]:
        """Return (datetime, all_day) from a Calendar start/end node."""
        if not node:
            return None, False
        if "date" in node:  # all-day event (date only)
            try:
                return datetime.fromisoformat(node["date"]), True
            except ValueError:
                return None, True
        if "dateTime" in node:
            try:
                return datetime.fromisoformat(node["dateTime"]), False
            except ValueError:
                return None, False
        return None, False

    @classmethod
    def _to_model(cls, account_id: int, raw: dict) -> CalendarEvent:
        start, all_day = cls._parse_endpoint(raw.get("start"))
        end, _ = cls._parse_endpoint(raw.get("end"))
        return CalendarEvent(
            account_id=account_id,
            external_id=raw["id"],
            calendar_id=_CALENDAR_ID,
            summary=raw.get("summary"),
            description=raw.get("description"),
            location=raw.get("location"),
            status=raw.get("status"),
            all_day=all_day,
            start=start,
            end=end,
        )

    @staticmethod
    def _to_summary(row: CalendarEvent) -> EventSummary:
        return EventSummary(
            id=row.id,
            external_id=row.external_id,
            summary=row.summary,
            location=row.location,
            all_day=row.all_day,
            start=row.start,
            end=row.end,
            status=row.status,
        )

    @staticmethod
    def _to_detail(row: CalendarEvent) -> EventDetail:
        return EventDetail(
            id=row.id,
            external_id=row.external_id,
            account_id=row.account_id,
            calendar_id=row.calendar_id,
            summary=row.summary,
            description=row.description,
            location=row.location,
            all_day=row.all_day,
            start=row.start,
            end=row.end,
            status=row.status,
        )
