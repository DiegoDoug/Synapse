"""Application configuration / settings.

Centralized settings loaded from environment variables (and an optional
.env file) via pydantic-settings. Defaults mirror backend/.env.example so
the app runs with zero configuration. No business logic.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Synapse backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Synapse"
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (SQLite file, per ARCHITECTURE.md)
    database_url: str = "sqlite:///data/synapse.db"

    # CORS — comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173"

    # Google OAuth 2.0 (Stage 2 — Gmail + Calendar). Empty by default so the
    # app still boots without credentials; connection routes require these.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/connections/google/callback"
    google_scopes: str = (
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/userinfo.email"
    )

    # Synchronization
    sync_interval_minutes: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def google_scopes_list(self) -> list[str]:
        """Parse the space-separated Google OAuth scopes into a list."""
        return [scope.strip() for scope in self.google_scopes.split() if scope.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (FastAPI dependency-friendly)."""
    return Settings()
