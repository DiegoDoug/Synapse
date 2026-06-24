"""Connection service — manage external account connections.

Business logic for the Google OAuth flow and account lifecycle. Orchestrates
the OAuth integration and the account repository; performs no HTTP itself
beyond delegating to the integration.
"""

from datetime import UTC, datetime

from backend.integrations.google.oauth import GoogleOAuthClient
from backend.models.account import Account
from backend.repositories.account_repository import AccountRepository
from backend.schemas.connection import AuthorizationUrlResponse, ConnectionRead
from backend.services.interfaces import ConnectionServiceInterface

_PROVIDER = "google"


class ConnectionService(ConnectionServiceInterface):
    """Connect, list, and disconnect Google accounts."""

    def __init__(
        self,
        accounts: AccountRepository,
        oauth: GoogleOAuthClient,
        user_id: int,
    ) -> None:
        self._accounts = accounts
        self._oauth = oauth
        self._user_id = user_id

    def build_authorization_url(self, user_id: int) -> AuthorizationUrlResponse:
        url, state = self._oauth.build_authorization_url()
        return AuthorizationUrlResponse(authorization_url=url, state=state)

    def complete_authorization(self, code: str, state: str) -> ConnectionRead:
        credentials = self._oauth.exchange_code(code)
        email = self._oauth.fetch_email(credentials)
        scopes = " ".join(credentials.scopes or [])
        now = datetime.now(UTC)

        account = self._accounts.get_by_provider_email(_PROVIDER, email)
        if account is not None:
            account.access_token = credentials.token
            # Google omits the refresh_token on re-consent; keep the stored one.
            account.refresh_token = credentials.refresh_token or account.refresh_token
            account.token_expiry = credentials.expiry
            account.scopes = scopes
            account.status = "connected"
            account.updated_at = now
            account = self._accounts.update(account)
        else:
            account = self._accounts.add(
                Account(
                    user_id=self._user_id,
                    provider=_PROVIDER,
                    email=email,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=credentials.expiry,
                    scopes=scopes,
                    status="connected",
                )
            )
        return self._to_read(account)

    def list_connections(self, user_id: int) -> list[ConnectionRead]:
        return [self._to_read(a) for a in self._accounts.list_for_user(user_id)]

    def disconnect(self, account_id: int) -> None:
        account = self._accounts.get(account_id)
        if account is None:
            raise LookupError(f"Account {account_id} not found")
        self._accounts.delete(account)

    @staticmethod
    def _to_read(account: Account) -> ConnectionRead:
        return ConnectionRead(
            id=account.id,
            provider=account.provider,
            email=account.email,
            scopes=account.scopes.split() if account.scopes else [],
            status=account.status,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
