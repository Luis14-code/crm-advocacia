#!/usr/bin/env bash
# Backup diário do PostgreSQL (pg_dump comprimido) com retenção.
# Uso (host): ./scripts/backup.sh   |   Agende via cron (BACKUP_CRON no .env).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Gerando backup..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-claudio}" "${POSTGRES_DB:-claudio}" \
  | gzip > "${BACKUP_DIR}/claudio_${STAMP}.sql.gz"

echo "Removendo backups com mais de ${RETENTION_DAYS} dias..."
find "$BACKUP_DIR" -name 'claudio_*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "Backup concluído: ${BACKUP_DIR}/claudio_${STAMP}.sql.gz"
