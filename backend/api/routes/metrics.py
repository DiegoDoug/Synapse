"""Prometheus metrics endpoint — GET /metrics (Stage 8 — observability).

Mounted at the app root (not under /api/v1) so scrape config matches the
conventional ``/metrics`` path. Returns 503 when the optional prometheus-client
dependency is not installed.
"""

from fastapi import APIRouter, Response

from backend.observability.metrics import metrics_available, render_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus metrics in the text exposition format."""
    body, content_type = render_metrics()
    status = 200 if metrics_available() else 503
    return Response(content=body, media_type=content_type, status_code=status)
