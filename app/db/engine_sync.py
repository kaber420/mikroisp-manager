# app/db/engine_sync.py
"""
Synchronous SQLModel database engine.
Shares the underlying connection pool with the async engine to prevent database locks.
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel
from app.db.engine import engine

# Share the engine's sync_engine to use the exact same connection pool
from app.core.config import settings
sync_engine = engine.sync_engine
DATABASE_URL_SYNC = settings.DATABASE_URL_SYNC


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

