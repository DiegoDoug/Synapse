#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/deploy-prod.sh — deploy the production stack (Stage 8).
#
# Pulls the target images, runs migrations safely, restarts services gracefully,
# health-checks the result, and auto-rolls-back on failure.
#
# Usage:
#   IMAGE_TAG=sha-abc123 REGISTRY=ghcr.io/owner/repo ./scripts/deploy-prod.sh
#
# Env:
#   ENV_FILE   default: .env.production
#   IMAGE_TAG  image tag to deploy (default: latest)
#   REGISTRY   image registry/namespace prefix (default: synapse)
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

export DEPLOY_ENV="production"
export ENV_FILE="${ENV_FILE:-.env.production}"
export STATE_DIR="${STATE_DIR:-.deploy-state/production}"

# shellcheck source=scripts/_lib.sh
source "$SCRIPT_DIR/_lib.sh"

log "Deploying PRODUCTION (tag=${IMAGE_TAG:-latest})."
run_deploy
