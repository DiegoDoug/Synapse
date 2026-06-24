"""Email service — read access and incremental Gmail synchronization.

Business logic for emails: maps raw Gmail payloads to EmailMessage rows,
performs incremental sync using a per-account historyId cursor, and exposes
synced messages as DTOs. Builds a GmailIntegration per account from that
account's (refreshed) credentials.
"""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from googleapiclient.errors import HttpError

from backend.integrations.google.gmail import GmailIntegration
from backend.integrations.google.oauth import GoogleOAuthClient
from backend.models.account import Account
from backend.models.email_message import EmailMessage
from backend.models.sync_state import SyncState
from backend.repositories.account_repository import AccountRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.sync_state_repository import SyncStateRepository
from backend.schemas.email import EmailDetail, EmailSummary
from backend.schemas.sync import SyncResult
from backend.services.interfaces import EmailServiceInterface

_RESOURCE = "gmail"
_INITIAL_SYNC_LIMIT = 50


class EmailService(EmailServiceInterface):
    """Read synced email and run incremental Gmail sync."""

    def __init__(
        self,
        accounts: AccountRepository,
        emails: EmailRepository,
        sync_states: SyncStateRepository,
        oauth: GoogleOAuthClient,
    ) -> None:
        self._accounts = accounts
        self._emails = emails
        self._sync_states = sync_states
        self._oauth = oauth

    # --- Reads -------------------------------------------------------------

    def list_messages(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[EmailSummary]:
        rows = self._emails.list_for_account(
            account_id, limit=limit, offset=offset, unread_only=unread_only
        )
        return [self._to_summary(row) for row in rows]

    def get_message(self, account_id: int, message_id: int) -> EmailDetail | None:
        row = self._emails.get(message_id)
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
            gmail = self._build_gmail(account)
            message_ids, new_cursor = self._collect_message_ids(gmail, state.cursor)

            created = updated = 0
            for message_id in message_ids:
                raw = gmail.get_message(message_id)
                if self._upsert_message(account_id, raw):
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
        except HttpError as exc:
            return self._fail(state, account_id, str(exc))
        except Exception as exc:  # noqa: BLE001 — surface any sync failure as state
            return self._fail(state, account_id, str(exc))

    # --- Internals ---------------------------------------------------------

    def _build_gmail(self, account: Account) -> GmailIntegration:
        credentials = self._oauth.credentials_from_tokens(
            account.access_token,
            account.refresh_token,
            account.token_expiry,
            account.scopes.split() if account.scopes else [],
        )
        if credentials.expired and credentials.refresh_token:
            self._oauth.refresh(credentials)
        self._pending_credentials = credentials
        return GmailIntegration(credentials)

    def _collect_message_ids(
        self, gmail: GmailIntegration, cursor: str | None
    ) -> tuple[list[str], str | None]:
        if cursor:
            try:
                return gmail.list_history(cursor)
            except HttpError as exc:
                # 404 => cursor expired; fall back to a full resync.
                if exc.resp.status != 404:
                    raise
        ids = gmail.list_recent_message_ids(_INITIAL_SYNC_LIMIT)
        new_cursor = gmail.get_profile().get("historyId")
        return ids, str(new_cursor) if new_cursor else cursor

    def _upsert_message(self, account_id: int, raw: dict) -> bool:
        """Insert or update a message. Returns True if newly created."""
        mapped = self._to_model(account_id, raw)
        existing = self._emails.get_by_external_id(account_id, mapped.external_id)
        if existing is None:
            self._emails.upsert(mapped)
            return True
        existing.thread_id = mapped.thread_id
        existing.sender = mapped.sender
        existing.recipient = mapped.recipient
        existing.subject = mapped.subject
        existing.snippet = mapped.snippet
        existing.labels = mapped.labels
        existing.is_read = mapped.is_read
        existing.received_at = mapped.received_at
        self._emails.upsert(existing)
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
    def _to_model(account_id: int, raw: dict) -> EmailMessage:
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }
        label_ids = raw.get("labelIds", [])
        received_at = None
        if (date_header := headers.get("date")) is not None:
            try:
                received_at = parsedate_to_datetime(date_header)
            except (TypeError, ValueError):
                received_at = None
        return EmailMessage(
            account_id=account_id,
            external_id=raw["id"],
            thread_id=raw.get("threadId"),
            sender=headers.get("from"),
            recipient=headers.get("to"),
            subject=headers.get("subject"),
            snippet=raw.get("snippet"),
            labels=" ".join(label_ids),
            is_read="UNREAD" not in label_ids,
            received_at=received_at,
        )

    @staticmethod
    def _to_summary(row: EmailMessage) -> EmailSummary:
        return EmailSummary(
            id=row.id,
            external_id=row.external_id,
            thread_id=row.thread_id,
            sender=row.sender,
            subject=row.subject,
            snippet=row.snippet,
            is_read=row.is_read,
            received_at=row.received_at,
        )

    @staticmethod
    def _to_detail(row: EmailMessage) -> EmailDetail:
        return EmailDetail(
            id=row.id,
            external_id=row.external_id,
            thread_id=row.thread_id,
            account_id=row.account_id,
            sender=row.sender,
            recipient=row.recipient,
            subject=row.subject,
            snippet=row.snippet,
            is_read=row.is_read,
            received_at=row.received_at,
            labels=row.labels.split() if row.labels else [],
        )
