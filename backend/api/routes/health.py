"""Health endpoints — liveness GET /api/v1/health, readiness /api/v1/health/ready.

Liveness answers "is the process up?" (used by Docker/orchestrator restart
policies). Readiness answers "can it serve traffic?" by checking the database
connection (used by deploy scripts to gate a release). Liveness stays a pure,
dependency-free check for backward compatibility.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.config import get_settings
from backend.database import engine
from backend.schemas.health import HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe: the process is running."""
    return HealthResponse(status="healthy")


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness() -> JSONResponse:
    """Readiness probe: dependencies (database) are reachable."""
    settings = get_settings()
    database_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — report unready, never raise.
        logger.error("Readiness check failed: database unreachable: %s", exc)
        database_ok = False

    body = ReadinessResponse(
        status="ready" if database_ok else "unready",
        environment=settings.environment,
        database=database_ok,
    )
    return JSONResponse(
        status_code=200 if database_ok else 503,
        content=body.model_dump(),
    )
