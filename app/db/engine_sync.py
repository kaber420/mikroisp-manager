# app/db/engine_sync.py
"""
Synchronous SQLModel database engine.
Supports SQLite (default) and PostgreSQL via DATABASE_URL_SYNC environment variable.
"""

import os
from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

# --- Database URL Configuration ---
# Read DATABASE_URL_SYNC from environment. If not set, default to SQLite.
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")

if DATABASE_URL_SYNC is None:
    # Default to SQLite in data/db/
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
    os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
    DATABASE_URL_SYNC = f"sqlite:///{DATABASE_FILE}"

# Detect dialect from URL
_is_sqlite = DATABASE_URL_SYNC.startswith("sqlite")

# Create SYNC engine with appropriate connect_args
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
sync_engine = create_engine(DATABASE_URL_SYNC, echo=False, connect_args=_connect_args)


# Activate WAL mode only for SQLite to improve concurrency
if _is_sqlite:
    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()


def get_sync_session() -> Generator[Session, None, None]:
    """
    Dependency for SYNC SQLModel session injection.
    """
    with Session(sync_engine) as session:
        yield session


def create_sync_db_and_tables():
    """
    Create all tables with SYNC engine.
    """
    SQLModel.metadata.create_all(sync_engine)
