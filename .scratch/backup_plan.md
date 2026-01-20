# Backup, WAL Mode, and Log Rotation Implementation Plan

## Goal Description

Enable WAL (Write-Ahead Logging) mode for SQLite to improve concurrency and allow hot backups. Implement a manual backup feature accessible via the web Settings interface, utilizing a shell script for the actual backup operation. Configure log rotation for the audit log to prevent disk space issues.

## User Review Required
>
> [!IMPORTANT]
> **WAL Mode Activation**: Enabling WAL mode creates `-wal` and `-shm` files alongside the database. This is generally safe but requires that all access to the DB uses the same SQLite version/library. The application uses `aiosqlite`/`SQLAlchemy`.
> **Backup Location**: Backups will be stored in `data/backups/`. Ensure this directory is persistent and backed up externally if needed.

## Proposed Changes

### Database Layer

#### [MODIFY] [engine.py](file:///home/kaber420/Documentos/python/umanager6/app/db/engine.py)

- Add `sqlalchemy.event` listener to `sync` connection (or execute on connect) to set `PRAGMA journal_mode=WAL;`.
- Ensure this runs for both sync and async engine connections if possible, or at least the primary writer.

### Backup functionality

#### [NEW] [scripts/db_backup.sh](file:///home/kaber420/Documentos/python/umanager6/scripts/db_backup.sh)

- Bash script to perform hot backup using `sqlite3 <db> ".backup <dest>"`.
- Arguments: `type` (manual/auto).
- Naming convention: `backup_<type>_<timestamp>.sqlite`.
- Retention: Delete manual backups older than 30 days (configurable).

#### [MODIFY] [app/api/settings/main.py](file:///home/kaber420/Documentos/python/umanager6/app/api/settings/main.py)

- Add `POST /settings/backup-now`.
- Use `subprocess.call` to execute `scripts/db_backup.sh`.
- Return success/failure status.

#### [MODIFY] [templates/settings.html](file:///home/kaber420/Documentos/python/umanager6/templates/settings.html)

- Add "Manual Backup" button in "Monitoring & Backups" section.
- Add status display area.

#### [NEW_OR_MODIFY] [static/js/settings.js](file:///home/kaber420/Documentos/python/umanager6/static/js/settings.js)

- Add event listener for Backup button.
- Call API and handle response coverage.

### Log Rotation

#### [MODIFY] [app/core/audit.py](file:///home/kaber420/Documentos/python/umanager6/app/core/audit.py)

- Replace `logging.FileHandler` with `logging.handlers.RotatingFileHandler`.
- Set max size (e.g., 5MB) and backup count (e.g., 5).

## Verification Plan

### Automated Tests

- None existing for this specific UI/Sysadmin feature.
- **Unit Test**: Create `tests/test_backup_script.py` (or manual run) to verify script creates file.
- **WAL Verification**: Check `PRAGMA journal_mode` via `sqlite3` CLI after app start.

### Manual Verification

1. **WAL Mode**:
    - Start app.
    - Run `sqlite3 data/db/inventory.sqlite "PRAGMA journal_mode;"` -> Expect `wal`.
    - Check for `.wal` file existence.
2. **Backup**:
    - Go to Settings > Monitoring & Backups.
    - Click "Backup Now".
    - Verify success message.
    - Check `data/backups/` for new file.
    - Verify backup integrity: `sqlite3 data/backups/<file> "PRAGMA integrity_check;"`.
3. **Log Rotation**:
    - (Hard to verify quickly without spamming logs, but code review of `RotatingFileHandler` is usually sufficient).
    - Can manually call `audit_logger` in a loop to force rotation if needed.
