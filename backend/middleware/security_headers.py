"""Security headers middleware (Stage 8 — API hardening).

Adds a conservative set of response headers that protect the API and the SPA it
serves behind the reverse proxy. HSTS is only meaningful behind TLS, so the
whole middleware is gated on ``security_headers_enabled`` (set in the production
env files, off in dev). No business logic.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "0",  # modern browsers; rely on CSP instead of legacy filter
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in _HEADERS.items():
            response.headers.setdefault(key, value)
        return response
