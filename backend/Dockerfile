# syntax=docker/dockerfile:1.7
# Multi-stage build for the Synapse FastAPI backend (Stage 8).
# Stage 1 compiles dependencies into a wheelhouse; stage 2 is a slim runtime
# image with no build toolchain, running as a non-root user.

# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Only the runtime requirements (no dev/test deps) go into the production image.
COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.11-slim AS runtime

# - PYTHONDONTWRITEBYTECODE: no .pyc clutter in the layer
# - PYTHONUNBUFFERED: logs flush immediately (structured JSON to stdout)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl is used by the container HEALTHCHECK to hit the readiness endpoint.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user (security hardening).
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Install dependencies from the prebuilt wheelhouse (no compilers in runtime).
COPY --from=builder /wheels /wheels
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-index --find-links=/wheels -r backend/requirements.txt \
    && rm -rf /wheels

# Application code. Copying after deps keeps the dependency layer cached across
# code-only changes.
COPY backend/ ./backend/
COPY docs/ ./docs/

# Writable data dir for the SQLite dev fallback / local volumes.
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

# Production server: uvicorn with multiple workers. Override the command in the
# worker service to run `python -m backend.worker`.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
