"""Central logging configuration (Stage 8 — observability).

Provides one log format across every service (backend API + automation worker).
``log_format="json"`` emits one structured JSON object per line for log
aggregators; ``"console"`` emits human-readable lines for local development.

The active request id (set by the request-id middleware) is attached to every
record via a contextvar, so a log line can always be correlated to the request
that produced it — the lightweight tracing required by Stage 8. No business
logic lives here.
"""

from __future__ import annotations

import contextvars
import datetime as _dt
import json
import logging

# Set by RequestIDMiddleware for the lifetime of a request; empty otherwise
# (e.g. scheduler/worker jobs, startup). Read by the log filter below.
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

# Standard LogRecord attributes we skip when collecting structured "extra" fields.
_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "request_id", "taskName"}


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record (empty when none)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", "")
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Surface any structured fields passed via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(log_format: str = "console", level: str = "INFO") -> None:
    """Configure the root logger once for the whole process.

    Idempotent: replaces existing handlers so repeated calls (tests, reload)
    do not stack duplicate output.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] "
                "[req=%(request_id)s] %(message)s"
            )
        )

    root.handlers = [handler]
    # Align uvicorn's loggers with our handler so access logs share the format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = [handler]
        logging.getLogger(name).propagate = False
