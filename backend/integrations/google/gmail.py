"""Gmail integration (integration layer).

Thin wrapper over the Gmail REST API (read-only). Returns raw API payloads;
mapping to domain models and persistence are the service layer's concern.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.integrations.base import Integration

# Headers we request in metadata-format message reads.
_METADATA_HEADERS = ["From", "To", "Subject", "Date"]


class GmailIntegration(Integration):
    """Read-only Gmail API client scoped to a single account's credentials."""

    resource = "gmail"

    def __init__(self, credentials: Credentials) -> None:
        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    @property
    def provider(self) -> str:
        return "google"

    def get_profile(self) -> dict:
        """Return the mailbox profile (includes the current historyId)."""
        return self._service.users().getProfile(userId="me").execute()

    def list_recent_message_ids(self, max_results: int) -> list[str]:
        """Return up to max_results recent message ids (newest first)."""
        ids: list[str] = []
        page_token: str | None = None
        while len(ids) < max_results:
            response = (
                self._service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=min(100, max_results - len(ids)),
                    pageToken=page_token,
                )
                .execute()
            )
            ids.extend(message["id"] for message in response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return ids[:max_results]

    def list_history(self, start_history_id: str) -> tuple[list[str], str | None]:
        """Return (added message ids, latest historyId) since start_history_id.

        Raises googleapiclient.errors.HttpError (404) if start_history_id is too
        old; the service layer treats that as a signal to do a full resync.
        """
        ids: list[str] = []
        latest = start_history_id
        page_token: str | None = None
        while True:
            response = (
                self._service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded"],
                    pageToken=page_token,
                )
                .execute()
            )
            latest = response.get("historyId", latest)
            for entry in response.get("history", []):
                for added in entry.get("messagesAdded", []):
                    ids.append(added["message"]["id"])
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        # De-duplicate while preserving order.
        seen: set[str] = set()
        unique = [mid for mid in ids if not (mid in seen or seen.add(mid))]
        return unique, str(latest) if latest else None

    def get_message(self, message_id: str) -> dict:
        """Return a single message in metadata format (headers + snippet)."""
        return (
            self._service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=_METADATA_HEADERS,
            )
            .execute()
        )
