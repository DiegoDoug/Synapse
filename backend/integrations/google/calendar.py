"""Google Calendar integration (integration layer).

Thin wrapper over the Calendar REST API. Reads return raw API payloads; the
write paths (``create_event`` / ``delete_event``) accept an already-assembled
event body. Mapping to domain models and persistence are the service layer's
concern.

Incremental sync uses Calendar's syncToken: the initial full list returns a
nextSyncToken, and subsequent calls pass it to receive only changes. A 410
Gone means the token expired and the caller must do a full resync.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.integrations.base import Integration


class GoogleCalendarIntegration(Integration):
    """Google Calendar API client scoped to one account."""

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

    def create_event(self, calendar_id: str, body: dict) -> dict:
        """Insert an event from an assembled body. Returns the created event.

        Requires a calendar write scope; a missing scope surfaces as an
        HttpError (403) for the service layer to translate.
        """
        return (
            self._service.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        """Delete an event by its provider id. Returns nothing on success."""
        self._service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
