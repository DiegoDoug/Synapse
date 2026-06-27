#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/rollback.sh — roll the stack back to the previous image tag (Stage 8).
#
# Reads the previously-deployed tag recorded by the deploy scripts and brings
# the stack back up on it. Invoked automatically by run_deploy() when a health
# check fails, and runnable manually for an operator-initiated rollback.
#
# Usage:
#   ./scripts/rollback.sh                 # roll back production (default)
#   DEPLOY_ENV=staging ./scripts/rollback.sh
#   ./scripts/rollback.sh <explicit-tag>  # roll back to a specific tag
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

export DEPLOY_ENV="${DEPLOY_ENV:-production}"
if [[ "$DEPLOY_ENV" == "staging" ]]; then
  export ENV_FILE="${ENV_FILE:-.env.staging}"
  export STATE_DIR="${STATE_DIR:-.deploy-state/staging}"
else
  export ENV_FILE="${ENV_FILE:-.env.production}"
  export STATE_DIR="${STATE_DIR:-.deploy-state/production}"
fi

# shellcheck source=scripts/_lib.sh
source "$SCRIPT_DIR/_lib.sh"
require_tools

TARGET_TAG="${1:-}"
if [[ -z "$TARGET_TAG" ]]; then
  TARGET_TAG="$(cat "$STATE_DIR/previous_tag" 2>/dev/null || echo "")"
fi
[[ -n "$TARGET_TAG" ]] || die "No previous tag recorded and none provided. Pass a tag explicitly."

export IMAGE_TAG="$TARGET_TAG"
log "Rolling back ${DEPLOY_ENV} to tag '${IMAGE_TAG}'."

pull_images
# Migrations are forward-only; rolling the schema back is a manual,
# backup-restore decision (see DEPLOYMENT.md). We only swap images here.
restart_services

if health_check; then
  echo "${IMAGE_TAG}" > "$STATE_DIR/current_tag"
  log "✅ Rollback to '${IMAGE_TAG}' healthy."
else
  die "Rollback to '${IMAGE_TAG}' is still unhealthy — manual intervention required."
fi
