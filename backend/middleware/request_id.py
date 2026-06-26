"""Request-ID propagation middleware (Stage 8 — lightweight tracing).

Reads an inbound correlation header (default ``X-Request-ID``) or mints a new
UUID, publishes it on the logging contextvar so every log line emitted while
handling the request carries it, and echoes it back on the response. Downstream
services and the reverse proxy can forward the same header to stitch a trace
together. No business logic.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.logging_config import request_id_ctx


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable request id to logs and the response headers."""

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self._header = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self._header) or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        # Expose it to handlers (e.g. for inclusion in error payloads).
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers[self._header] = request_id
        return response
