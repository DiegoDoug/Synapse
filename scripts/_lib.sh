#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/_lib.sh — shared deployment helpers (Stage 8).
# Sourced by deploy-prod.sh, deploy-staging.sh, and rollback.sh. Not executable
# on its own.
# -----------------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
STATE_DIR="${STATE_DIR:-.deploy-state}"

log()  { echo -e "[$(date -u +%H:%M:%S)] $*"; }
die()  { echo -e "[ERROR] $*" >&2; exit 1; }

# compose <args...> — run docker compose with the active env + compose file.
compose() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

require_tools() {
  command -v docker >/dev/null 2>&1 || die "docker is not installed."
  docker compose version >/dev/null 2>&1 || die "docker compose v2 is required."
  [[ -f "$ENV_FILE" ]] || die "Env file '$ENV_FILE' not found."
  [[ -f "$COMPOSE_FILE" ]] || die "Compose file '$COMPOSE_FILE' not found."
}

# Record the currently-deployed image tag so rollback can return to it.
save_previous_tag() {
  mkdir -p "$STATE_DIR"
  local current
  current="$(cat "$STATE_DIR/current_tag" 2>/dev/null || echo "")"
  if [[ -n "$current" ]]; then
    echo "$current" > "$STATE_DIR/previous_tag"
  fi
  echo "${IMAGE_TAG:-latest}" > "$STATE_DIR/current_tag"
}

pull_images() {
  log "Pulling images (tag=${IMAGE_TAG:-latest})..."
  compose pull
}

# Run schema migrations in a one-shot container before swapping the app over.
run_migrations() {
  log "Running database migrations..."
  compose run --rm --no-deps backend python -m backend.migrate \
    || die "Migrations failed; aborting deploy (no services restarted)."
}

restart_services() {
  log "Starting/refreshing services (graceful, rolling where possible)..."
  # --remove-orphans cleans up services dropped from the compose file.
  compose up -d --remove-orphans
}

# Poll the backend readiness endpoint via the running backend container.
# Returns non-zero if it never becomes ready within the timeout.
health_check() {
  local retries="${HEALTHCHECK_RETRIES:-30}"
  local delay="${HEALTHCHECK_DELAY:-5}"
  log "Waiting for backend readiness (up to $((retries * delay))s)..."
  for ((i = 1; i <= retries; i++)); do
    if compose exec -T backend curl -fsS http://localhost:8000/api/v1/health/ready >/dev/null 2>&1; then
      log "Backend is ready."
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

# Standard deploy sequence shared by prod + staging, with auto-rollback.
run_deploy() {
  require_tools
  save_previous_tag
  pull_images
  run_migrations
  restart_services
  if health_check; then
    log "✅ Deployment healthy (env=${DEPLOY_ENV}, tag=${IMAGE_TAG:-latest})."
  else
    log "❌ Health check FAILED — triggering automatic rollback."
    compose logs --tail=50 backend || true
    "${SCRIPT_DIR}/rollback.sh" || die "Rollback also failed; manual intervention required."
    die "Deployment rolled back after failed health check."
  fi
}
