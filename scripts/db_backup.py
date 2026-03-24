import argparse
import sys
import os

# Ensure we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_backup_service import perform_db_backup, clean_old_backups, RETENTION_DAYS

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup SQLite Database")
    parser.add_argument("type", nargs="?", default="manual", choices=["manual", "auto"], help="Backup type tag")
    args = parser.parse_args()
    
    if perform_db_backup(backup_type=args.type):
        clean_old_backups(RETENTION_DAYS)
        sys.exit(0)
    else:
        sys.exit(1)
