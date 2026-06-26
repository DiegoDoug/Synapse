"""Fixed-window rate limiting middleware (Stage 8 — API security).

A dependency-free, per-client fixed-window limiter: each client (identified by
the forwarded client IP) gets ``limit`` requests per ``window`` seconds. State is
held in-process, which is correct for the single-node production target; when a
Redis URL is configured the limiter uses it so multiple backend replicas share
one counter. It fails open (allows the request) if Redis is unreachable — a
limiter must never take the API down.

Returns HTTP 429 with a ``Retry-After`` header when the window is exhausted.
Off by default (``rate_limit_enabled=false``) so dev and tests are unaffected.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths exempt from limiting: health + metrics must stay scrapeable by the
# orchestrator and Prometheus even under load.
_EXEMPT_PREFIXES = ("/api/v1/health", "/metrics")


class _InMemoryWindow:
    """Per-key fixed-window counters kept in this process."""

    def __init__(self) -> None:
        self._hits: dict[str, tuple[int, float]] = {}

    def incr(self, key: str, window: int) -> tuple[int, float]:
        now = time.monotonic()
        count, start = self._hits.get(key, (0, now))
        if now - start >= window:
            count, start = 0, now
        count += 1
        self._hits[key] = (count, start)
        # Opportunistic cleanup so the dict cannot grow without bound.
        if len(self._hits) > 10_000:
            cutoff = now - window
            self._hits = {
                k: v for k, v in self._hits.items() if v[1] >= cutoff
            }
        return count, start + window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit requests per client IP using a fixed window."""

    def __init__(
        self,
        app,
        limit: int = 100,
        window: int = 60,
        redis_url: str = "",
    ) -> None:
        super().__init__(app)
        self._limit = limit
        self._window = window
        self._memory = _InMemoryWindow()
        self._redis = None
        if redis_url:
            self._redis = _try_redis(redis_url)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        key = self._client_key(request)
        count, reset_at = self._increment(key)
        if count > self._limit:
            retry_after = max(1, int(reset_at - time.monotonic()))
            logger.warning("Rate limit exceeded for %s (%d req).", key, count)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self._limit - count)
        )
        return response

    def _increment(self, key: str) -> tuple[int, float]:
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, self._window)
                count, _ = pipe.execute()
                return int(count), time.monotonic() + self._window
            except Exception:  # noqa: BLE001 — fail open on any Redis error.
                logger.warning("Redis rate-limit backend unavailable; failing open.")
                return 0, time.monotonic() + self._window
        return self._memory.incr(key, self._window)

    @staticmethod
    def _client_key(request: Request) -> str:
        # Honour the proxy's forwarded client when present (we sit behind nginx).
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ratelimit:{client_ip}"


def _try_redis(redis_url: str):
    """Return a Redis client, or None when the library/connection is absent."""
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception:  # noqa: BLE001 — degrade to in-memory limiting.
        logger.warning("Redis unavailable for rate limiting; using in-memory window.")
        return None
