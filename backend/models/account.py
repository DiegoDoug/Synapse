"""Account model (SQLModel). Schema only — no business logic.

An Account is a connected external account (e.g. a Google account reached via
OAuth 2.0). It stores the tokens needed by the integration layer to call the
provider's APIs on the user's behalf.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Account(SQLModel, table=True):
    """A connected external account and its OAuth credentials."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)

    # Provider identity
    provider: str = Field(index=True)  # e.g. "google"
    email: str = Field(index=True)  # the connected account's email address

    # OAuth 2.0 credentials (managed by ConnectionService)
    access_token: str
    refresh_token: str | None = Field(default=None)
    token_expiry: datetime | None = Field(default=None)
    scopes: str = Field(default="")  # space-separated granted scopes

    # Lifecycle
    status: str = Field(default="connected")  # connected | disconnected | error

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
