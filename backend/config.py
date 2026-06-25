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

    # Telegram (Stage 3 — notification delivery + inbound commands). Empty by
    # default so the app boots without a bot; delivery is skipped when unset.
    telegram_bot_token: str = ""
    telegram_default_chat_id: str = ""
    telegram_api_base: str = "https://api.telegram.org"

    # Notification scheduling (Stage 3 — APScheduler). The scheduler starts in
    # the app lifespan; tests that don't enter the lifespan never start it.
    scheduler_enabled: bool = True
    notification_poll_minutes: int = 15  # compose + deliver cadence
    daily_summary_hour: int = 8  # UTC hour for the daily summary (0-23)

    # AI layer (Stage 4). The active provider is swappable via AI_PROVIDER;
    # credentials are empty by default so the app boots without AI configured.
    ai_provider: str = "anthropic"  # anthropic | openai | ollama
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ai_max_tokens: int = 1024
    ai_temperature: float = 0.7

    @property
    def telegram_enabled(self) -> bool:
        """True when a bot token is configured."""
        return bool(self.telegram_bot_token)

    @property
    def ai_enabled(self) -> bool:
        """True when the active provider has what it needs to attempt a call.

        Ollama needs no key (a base URL is enough); the cloud providers need
        their API key. Reachability is only known at call time.
        """
        provider = self.ai_provider.lower()
        if provider == "anthropic":
            return bool(self.anthropic_api_key)
        if provider == "openai":
            return bool(self.openai_api_key)
        if provider == "ollama":
            return bool(self.ollama_base_url)
        return False

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
