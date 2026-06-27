"""Health-check response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body for the liveness endpoint."""

    status: str


class ReadinessResponse(BaseModel):
    """Response body for the readiness endpoint (Stage 8)."""

    status: str
    environment: str
    database: bool
