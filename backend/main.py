"""FastAPI application entrypoint.

Builds the app, configures logging and cross-cutting middleware (request-id,
metrics, rate limiting, security headers, CORS), validates the runtime
configuration, creates database tables on startup, and mounts the versioned API
router plus the /metrics endpoint. No business logic.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import api_router
from backend.api.routes.metrics import router as metrics_router
from backend.config import get_settings
from backend.database import create_db_and_tables
from backend.logging_config import configure_logging
from backend.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from backend.observability.metrics import MetricsMiddleware
from backend.scheduler import create_scheduler
from backend.services.workflow_scheduler import set_workflow_scheduler

settings = get_settings()
configure_logging(log_format=settings.log_format, level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: validate config, create tables, run the scheduler."""
    problems = settings.validate_runtime()
    if problems:
        joined = "; ".join(problems)
        # Fail fast in production; warn (and keep booting) in dev/staging.
        if settings.is_production:
            raise RuntimeError(f"Invalid production configuration: {joined}")
        logger.warning("Configuration warnings: %s", joined)

    create_db_and_tables()
    scheduler = create_scheduler(settings)
    if scheduler is not None:
        scheduler.start()
        logger.info("Notification scheduler started.")
    app.state.scheduler = scheduler
    logger.info(
        "Application started.",
        extra={"environment": settings.environment, "app": settings.app_name},
    )
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        set_workflow_scheduler(None)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Middleware is applied bottom-up: the last added wraps the request first.
# Order (outer -> inner): RequestID -> CORS -> SecurityHeaders -> RateLimit -> Metrics.
app.add_middleware(MetricsMiddleware)

if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.rate_limit_requests,
        window=settings.rate_limit_window_seconds,
        redis_url=settings.redis_url,
    )

if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware, header_name=settings.request_id_header)

app.include_router(api_router, prefix="/api/v1")
app.include_router(metrics_router)
