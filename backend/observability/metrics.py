"""Prometheus metrics (Stage 8 — observability).

Exposes basic RED-style metrics (request Rate, Errors, Duration) and a
``/metrics`` scrape endpoint. ``prometheus-client`` is imported lazily so the
app still boots when the optional dependency is absent: in that case the
middleware is a no-op and the endpoint reports unavailable, matching the
graceful-degradation pattern used elsewhere in the codebase. No business logic.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:  # Optional dependency — degrade gracefully when not installed.
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _AVAILABLE = True
except Exception:  # noqa: BLE001
    _AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


if _AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests.",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds.",
        ["method", "path"],
    )


def metrics_available() -> bool:
    """True when prometheus-client is installed and metrics can be collected."""
    return _AVAILABLE


def render_metrics() -> tuple[bytes, str]:
    """Return the current metrics exposition and its content type."""
    if not _AVAILABLE:
        return b"prometheus-client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


def _route_label(request: Request) -> str:
    """Use the matched route template (low cardinality), not the raw path.

    ``/api/v1/workflows/42`` collapses to ``/api/v1/workflows/{id}`` so a metric
    series is not created per id. Falls back to the literal path pre-routing.
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request count + latency for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _AVAILABLE:
            return await call_next(request)

        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            path = _route_label(request)
            REQUEST_COUNT.labels(request.method, path, str(status)).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
