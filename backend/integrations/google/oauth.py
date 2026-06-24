"""Google OAuth 2.0 client (integration layer).

Thin wrapper over google-auth-oauthlib / google-auth. Handles the
authorization-code flow, token exchange, credential refresh, and reading the
connected account's email address. No business logic, no database access — the
service layer persists tokens and decides when to refresh.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from backend.integrations.base import Integration

# Google frequently returns a superset of the requested scopes (e.g. it adds
# "openid"). Relaxing avoids oauthlib raising on that benign mismatch.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleOAuthClient(Integration):
    """OAuth 2.0 client for Google accounts."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = scopes

    @property
    def provider(self) -> str:
        return "google"

    def _client_config(self) -> dict:
        return {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": _AUTH_URI,
                "token_uri": _TOKEN_URI,
                "redirect_uris": [self._redirect_uri],
            }
        }

    def _flow(self) -> Flow:
        return Flow.from_client_config(
            self._client_config(),
            scopes=self._scopes,
            redirect_uri=self._redirect_uri,
        )

    def build_authorization_url(self) -> tuple[str, str]:
        """Return (authorization_url, state) for the consent screen."""
        url, state = self._flow().authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return url, state

    def exchange_code(self, code: str) -> Credentials:
        """Exchange an authorization code for OAuth credentials."""
        flow = self._flow()
        flow.fetch_token(code=code)
        return flow.credentials

    def credentials_from_tokens(
        self,
        access_token: str,
        refresh_token: str | None,
        token_expiry,
        scopes: list[str],
    ) -> Credentials:
        """Rebuild a Credentials object from stored token fields."""
        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=_TOKEN_URI,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=scopes,
            expiry=token_expiry,
        )

    def refresh(self, credentials: Credentials) -> Credentials:
        """Refresh an access token in place using the refresh token."""
        credentials.refresh(Request())
        return credentials

    def fetch_email(self, credentials: Credentials) -> str:
        """Return the connected account's email address (userinfo)."""
        service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        return service.userinfo().get().execute()["email"]
