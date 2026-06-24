"""Health endpoint — GET /api/v1/health."""

from fastapi import APIRouter

from backend.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="healthy")
