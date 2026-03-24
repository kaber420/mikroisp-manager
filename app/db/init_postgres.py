# app/db/init_postgres.py
"""
Database-agnostic initialization for default data using SQLModel ORM.
For PostgreSQL (or any SQL database) that doesn't use raw SQLite DDL.
"""

import logging
from sqlmodel import Session, select

from app.models.setting import Setting

logger = logging.getLogger(__name__)


def init_default_settings(session: Session) -> None:
    """
    Populate default settings using SQLModel if they don't exist.
    This is dialect-agnostic and works for both SQLite and PostgreSQL.
    """
    default_settings = [
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

    for key, value in default_settings:
        existing = session.exec(select(Setting).where(Setting.key == key)).first()
        if existing is None:
            setting = Setting(key=key, value=value)
            session.add(setting)
            logger.debug(f"Default setting added: {key}")

    session.commit()
    logger.info("✅ Default settings initialized (ORM-based).")


def init_db(session: Session) -> None:
    """
    Main entry point for ORM-based database initialization.
    """
    logger.info("🔧 [init_postgres] Initializing default data via ORM...")
    init_default_settings(session)
