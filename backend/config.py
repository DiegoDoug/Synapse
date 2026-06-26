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

    # Database. SQLite by default (zero-ops, per ARCHITECTURE.md); set a
    # postgresql+psycopg:// URL in production (Stage 8). The engine in
    # backend/database.py adapts pooling/connect args to the driver.
    database_url: str = "sqlite:///data/synapse.db"
    # Connection pool sizing (ignored by SQLite). Tuned conservatively for a
    # single-node deployment behind PgBouncer or direct Postgres.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30  # seconds to wait for a free connection
    db_pool_recycle: int = 1800  # recycle connections after 30 min

    # CORS — comma-separated list of allowed frontend origins. A literal "*"
    # is rejected in production by validate_runtime() (no wildcard in prod).
    cors_origins: str = "http://localhost:5173"

    # Redis (Stage 8 — optional). Used by the rate limiter and the worker as a
    # shared backend when set; the app falls back to in-process state when empty.
    redis_url: str = ""

    # Google OAuth 2.0 (Stage 2 — Gmail + Calendar). Empty by default so the
    # app still boots without credentials; connection routes require these.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/connections/google/callback"
    # Read scopes power Stage 2 sync; the send/events write scopes power the
    # Stage 4.5 external write tools (send_email, create/delete_calendar_event).
    # Adding scopes requires re-consent for already-connected accounts.
    google_scopes: str = (
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/calendar.events "
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

    # Automation (Stage 7). The event evaluator polls already-synced data and
    # fires event-triggered workflows when new rows appear since their cursor.
    workflow_event_poll_minutes: int = 2

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

    # Knowledge base / RAG (Stage 5). Embeddings (sentence-transformers) and the
    # Qdrant client are imported lazily by their integrations, so the app boots
    # without them: ingestion records documents as "unavailable" until installed,
    # and the vector store falls back to an in-process index. Install the extras
    # via backend/requirements-knowledge.txt to enable real semantic search.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 output size
    vector_backend: str = "memory"  # memory | qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "synapse_knowledge"
    knowledge_chunk_size: int = 1000  # chars per chunk
    knowledge_chunk_overlap: int = 150  # chars carried between chunks
    knowledge_max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Voice interface (Stage 4.7 — local STT/TTS). Models are imported lazily by
    # their integration clients, so the app boots without the (heavy) voice
    # dependencies installed; the endpoints report unavailable until then.
    # faster-whisper model size: tiny | small | medium (see ROADMAP).
    whisper_model: str = "small"
    whisper_device: str = "cpu"  # cpu | cuda
    whisper_compute_type: str = "int8"  # int8 | float16 | float32
    # Kokoro TTS voice + sample rate.
    tts_voice: str = "af_heart"
    tts_sample_rate: int = 24000
    # Reject uploads larger than this (push-to-talk clips are short).
    voice_max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Wake-word mode (Stage 4.7 MF2 — openWakeWord, opt-in). Audio streams to the
    # /voice/ws WebSocket as 16 kHz int16 PCM. openWakeWord ships pretrained
    # models; a personalized "Hey Synapse" model is future work (see ROADMAP).
    wake_word_model: str = "hey_jarvis"
    wake_word_threshold: float = 0.5  # detection score in [0, 1]
    voice_sample_rate: int = 16000  # PCM sample rate for streaming + STT
    # End-of-utterance: trailing silence (ms) that ends recording after a wake.
    voice_silence_ms: int = 800
    # Hard cap on a single recorded utterance.
    voice_max_utterance_ms: int = 15000
    # RMS below this (int16 scale) counts as silence for the energy VAD.
    voice_silence_rms: int = 500

    # --- Stage 8: Observability ------------------------------------------------
    # Log rendering: "json" emits one structured object per line (production,
    # log-aggregator friendly); "console" emits human-readable lines (dev).
    log_format: str = "console"  # json | console
    log_level: str = "INFO"
    # Expose Prometheus metrics at /metrics. Degrades to 503 when the optional
    # prometheus-client dependency is not installed.
    metrics_enabled: bool = True
    # Inbound/outbound correlation header for request-id propagation + tracing.
    request_id_header: str = "X-Request-ID"

    # --- Stage 8: Security hardening -------------------------------------------
    # Token-bucket / fixed-window rate limiting on the API. Off by default so
    # dev and the test suite are unaffected; enabled in the production env files.
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100  # allowed requests per window, per client
    rate_limit_window_seconds: int = 60
    # Send HSTS + other hardening headers (enable only behind TLS termination).
    security_headers_enabled: bool = False
    # Mark auth/session cookies Secure + HttpOnly + SameSite (set in prod).
    secure_cookies: bool = False
    # Access-token lifetime (minutes) for token-expiry enforcement.
    access_token_expire_minutes: int = 60

    @property
    def is_production(self) -> bool:
        """True when running under the production environment profile."""
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_staging(self) -> bool:
        """True when running under the staging environment profile."""
        return self.environment.lower() == "staging"

    def validate_runtime(self) -> list[str]:
        """Return a list of fatal misconfigurations for the active environment.

        Fail-fast guard called at startup. In production it enforces the Stage 8
        security baseline (no wildcard CORS, no SQLite, no debug, configured
        secrets); in dev/staging it returns an empty list so the app boots with
        zero configuration. Never raises — the caller decides how to react.
        """
        problems: list[str] = []
        if not (self.is_production or self.is_staging):
            return problems

        if self.is_production:
            if self.debug:
                problems.append("DEBUG must be false in production.")
            if "*" in self.cors_origins_list:
                problems.append("CORS_ORIGINS must not contain '*' in production.")
            if not self.cors_origins_list:
                problems.append("CORS_ORIGINS must be set in production.")
            if self.database_url.startswith("sqlite"):
                problems.append(
                    "DATABASE_URL must point to PostgreSQL in production, not SQLite."
                )
            if self.ai_provider.lower() != "ollama" and not self.ai_enabled:
                problems.append(
                    f"AI provider '{self.ai_provider}' is selected but its API key is unset."
                )
        return problems

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
