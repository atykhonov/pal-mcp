#!/bin/sh
set -e

# Configuration
BACKUP_KEEP="${BACKUP_KEEP:-20}"
SOURCE_DIR="${SOURCE_DIR:-./data/meilisearch}"
BACKUP_DIR="${BACKUP_DIR:-./data/meilisearch-backups}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="meili_backup_${TIMESTAMP}.tar.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$TIMESTAMP] Starting backup..."

# Create backup
cd "$SOURCE_DIR"
tar -czf "$BACKUP_DIR/$BACKUP_NAME" .

echo "[$TIMESTAMP] Created $BACKUP_NAME"

# Rotate old backups (keep last BACKUP_KEEP)
cd "$BACKUP_DIR"
ls -t meili_backup_*.tar.gz 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -f

CURRENT_COUNT=$(ls -1 meili_backup_*.tar.gz 2>/dev/null | wc -l)
echo "[$TIMESTAMP] Backup complete. Total backups: $CURRENT_COUNT (keeping last $BACKUP_KEEP)"
