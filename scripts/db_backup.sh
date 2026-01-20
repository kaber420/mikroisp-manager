#!/bin/bash
# db_backup.sh - Safe hot backup script for SQLite with WAL mode
# Usage: ./scripts/db_backup.sh [manual|auto]

set -e

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_FILE="$PROJECT_ROOT/data/db/inventory.sqlite"
BACKUP_DIR="$PROJECT_ROOT/data/backups"
RETENTION_DAYS=30

# --- Argument Handling ---
BACKUP_TYPE="${1:-manual}"
if [[ "$BACKUP_TYPE" != "manual" && "$BACKUP_TYPE" != "auto" ]]; then
    echo "Error: Invalid backup type. Use 'manual' or 'auto'."
    exit 1
fi

# --- Pre-flight Checks ---
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file not found at $DB_FILE"
    exit 1
fi

if ! command -v sqlite3 &> /dev/null; then
    echo "Error: sqlite3 command not found. Please install SQLite3."
    exit 1
fi

# --- Backup Execution ---
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="backup_${BACKUP_TYPE}_${TIMESTAMP}.sqlite"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILENAME"

echo "Starting $BACKUP_TYPE backup..."
echo "Source: $DB_FILE"
echo "Destination: $BACKUP_PATH"

# Use VACUUM INTO for a clean, consistent hot backup (SQLite 3.27+)
# This is safer than .backup for WAL mode as it creates a standalone DB.
sqlite3 "$DB_FILE" "VACUUM INTO '$BACKUP_PATH';"

if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_FILENAME"
else
    echo "Error: Backup failed."
    exit 1
fi

# --- Retention Policy ---
echo "Applying retention policy: deleting backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup_*.sqlite" -type f -mtime +$RETENTION_DAYS -delete -print

echo "Backup complete."
exit 0
