#!/usr/bin/env bash
# Back up the PostgreSQL database to a timestamped custom-format dump.
#
#   POSTGRES_DB=onikisepet POSTGRES_USER=app POSTGRES_HOST=... \
#     ./scripts/backup_database.sh
#
# Reads the same environment variables the application uses, so a backup taken
# from a deployed shell always targets the database that app is actually using.
set -euo pipefail

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_HOST:?POSTGRES_HOST is required}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%SZ)"
OUTPUT_FILE="${BACKUP_DIR}/onikisepet_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
  --dbname="${POSTGRES_DB}" \
  --host="${POSTGRES_HOST}" \
  ${POSTGRES_PORT:+--port="${POSTGRES_PORT}"} \
  ${POSTGRES_USER:+--username="${POSTGRES_USER}"} \
  --no-password \
  --format=custom \
  --file="${OUTPUT_FILE}"

echo "Backup written: ${OUTPUT_FILE}"
echo "Restore with: pg_restore --dbname=... --clean ${OUTPUT_FILE}"
