#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/restore-db.sh — restore a PostgreSQL backup (Stage 8).
#
# Restores a gzipped pg_dump archive produced by backup-db.sh into the running
# `postgres` compose service. Used by rollback.sh and for disaster recovery.
#
# Usage:
#   ./scripts/restore-db.sh ./backups/synapse-synapse-20260101T000000Z.sql.gz
# -----------------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
  echo "Usage: $0 <backup.sql.gz>" >&2
  exit 2
fi

if [[ -f "$ENV_FILE" ]]; then
  POSTGRES_USER="$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
  POSTGRES_DB="$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
fi
POSTGRES_USER="${POSTGRES_USER:-synapse}"
POSTGRES_DB="${POSTGRES_DB:-synapse}"

echo "[restore-db] Restoring ${ARCHIVE} into '${POSTGRES_DB}'..."
gunzip -c "$ARCHIVE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "[restore-db] Restore complete."
