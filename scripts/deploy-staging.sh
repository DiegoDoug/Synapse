#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/deploy-staging.sh — deploy the staging stack (Stage 8).
#
# Identical flow to deploy-prod.sh but against the staging env file. Feature
# branches deploy here automatically from the Deploy workflow.
#
# Usage:
#   IMAGE_TAG=sha-abc123 REGISTRY=ghcr.io/owner/repo ./scripts/deploy-staging.sh
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

export DEPLOY_ENV="staging"
export ENV_FILE="${ENV_FILE:-.env.staging}"
export STATE_DIR="${STATE_DIR:-.deploy-state/staging}"

# shellcheck source=scripts/_lib.sh
source "$SCRIPT_DIR/_lib.sh"

log "Deploying STAGING (tag=${IMAGE_TAG:-latest})."
run_deploy
