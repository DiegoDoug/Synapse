"""Connection (account) request/response schemas.

DTOs for the account-connection API. Tokens are never serialized to clients.
"""

from datetime import datetime

from pydantic import BaseModel


class ConnectionRead(BaseModel):
    """A connected account, safe for client exposure (no tokens)."""

    id: int
    provider: str
    email: str
    scopes: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class AuthorizationUrlResponse(BaseModel):
    """The provider authorization URL the user must visit to grant access."""

    authorization_url: str
    state: str
