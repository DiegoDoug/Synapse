#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/backup-db.sh — PostgreSQL backup with rotation (Stage 8).
#
# Dumps the production database from the running `postgres` compose service to a
# timestamped, compressed archive and prunes backups older than the retention
# window. Safe to run from cron.
#
# Usage:
#   ./scripts/backup-db.sh [--env-file .env.production] [--out ./backups]
#
# Env (overridable):
#   COMPOSE_FILE       default: docker-compose.prod.yml
#   ENV_FILE           default: .env.production
#   BACKUP_DIR         default: ./backups
#   RETENTION_DAYS     default: 14
# -----------------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --out) BACKUP_DIR="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Load DB name/user from the env file (only the keys we need).
# shellcheck disable=SC1090
if [[ -f "$ENV_FILE" ]]; then
  POSTGRES_USER="$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
  POSTGRES_DB="$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
fi
POSTGRES_USER="${POSTGRES_USER:-synapse}"
POSTGRES_DB="${POSTGRES_DB:-synapse}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
outfile="${BACKUP_DIR}/synapse-${POSTGRES_DB}-${timestamp}.sql.gz"

echo "[backup-db] Dumping database '${POSTGRES_DB}' -> ${outfile}"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  | gzip -9 > "$outfile"

# Verify the dump is non-empty before pruning anything.
if [[ ! -s "$outfile" ]]; then
  echo "[backup-db] ERROR: backup is empty; aborting." >&2
  rm -f "$outfile"
  exit 1
fi

echo "[backup-db] Wrote $(du -h "$outfile" | cut -f1) backup."
echo "[backup-db] Pruning backups older than ${RETENTION_DAYS} days."
find "$BACKUP_DIR" -name 'synapse-*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -print -delete

echo "[backup-db] Done."
