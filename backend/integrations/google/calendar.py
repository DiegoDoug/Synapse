"""Google Calendar integration (integration layer).

Thin wrapper over the Calendar REST API (read-only). Returns raw API payloads;
mapping to domain models and persistence are the service layer's concern.

Incremental sync uses Calendar's syncToken: the initial full list returns a
nextSyncToken, and subsequent calls pass it to receive only changes. A 410
Gone means the token expired and the caller must do a full resync.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.integrations.base import Integration


class GoogleCalendarIntegration(Integration):
    """Read-only Google Calendar API client scoped to one account."""

    resource = "calendar"

    def __init__(self, credentials: Credentials) -> None:
        self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    @property
    def provider(self) -> str:
        return "google"

    def list_events(
        self,
        calendar_id: str = "primary",
        sync_token: str | None = None,
        max_results: int = 250,
    ) -> tuple[list[dict], str | None]:
        """Return (events, next_sync_token) for a full or incremental list.

        Raises googleapiclient.errors.HttpError (410) if sync_token has expired;
        the service layer treats that as a signal to do a full resync.
        orderBy is intentionally omitted — it cannot be combined with syncToken.
        """
        events: list[dict] = []
        page_token: str | None = None
        next_sync_token: str | None = None
        while True:
            params: dict = {
                "calendarId": calendar_id,
                "singleEvents": True,
                "showDeleted": True,
                "maxResults": max_results,
                "pageToken": page_token,
            }
            if sync_token:
                params["syncToken"] = sync_token
            response = self._service.events().list(**params).execute()
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                next_sync_token = response.get("nextSyncToken")
                break
        return events, next_sync_token
