# app/db/init_db.py
"""
SQLite-specific post-initialization: seeds default settings.

Table creation is handled entirely by SQLModel.metadata.create_all()
in engine_sync.create_sync_db_and_tables(), called by bootstrap_system().
This module only inserts default rows when tables are empty.
"""

from sqlmodel import Session, select

from app.db.engine_sync import sync_engine
from app.models.setting import Setting


# Default application settings (inserted only when the settings table is empty)
_DEFAULT_SETTINGS: list[tuple[str, str]] = [
    ("company_name", "Mi ISP"),
    ("notification_email", "isp@example.com"),
    ("billing_alert_days", "3"),
    ("currency_symbol", "$"),
    ("telegram_bot_token", ""),
    ("telegram_chat_id", ""),
    ("client_bot_token", ""),
    ("days_before_due", "5"),
    ("default_monitor_interval", "300"),
    ("dashboard_refresh_interval", "5"),
    ("suspension_run_hour", "02:00"),
    ("db_backup_run_hour", "04:00"),
    ("cpe_stale_cycles", "3"),
]


def setup_databases() -> None:
    """Seed default settings into the database using the ORM."""
    print("Configurando datos iniciales (settings)...")
    _seed_default_settings()
    print("Configuración de datos iniciales completada.")


def _seed_default_settings() -> None:
    """Insert default settings only if they don't already exist."""
    with Session(sync_engine) as session:
        for key, value in _DEFAULT_SETTINGS:
            existing = session.exec(
                select(Setting).where(Setting.key == key)
            ).first()
            if existing is None:
                session.add(Setting(key=key, value=value))
        session.commit()
