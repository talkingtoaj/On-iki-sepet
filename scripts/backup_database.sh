#!/usr/bin/env bash
# PostgreSQL yedekleme (Cloud SQL veya doğrudan bağlantı).
# Kullanım: DATABASE_URL=postgres://... ./scripts/backup_database.sh
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL ortam değişkeni gerekli." >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="${BACKUP_DIR}/oniki_sepet_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"
pg_dump "${DATABASE_URL}" --format=custom --file="${OUTPUT_FILE}"

echo "Yedek oluşturuldu: ${OUTPUT_FILE}"
