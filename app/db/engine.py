# app/db/engine.py
"""
SQLModel database engine and session management for FastAPI Users integration.
Uses AsyncSession for compatibility with fastapi-users-db-sqlalchemy.
Configured with WAL mode for improved concurrency.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Read database path from environment or use default in data/db/
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
# Use aiosqlite for async support with SQLite
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


# Activar WAL mode para mejorar concurrencia y evitar "database is locked"
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()

# Create session maker
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for async SQLModel session injection.
    Usage: session: AsyncSession = Depends(get_session)
    """
    async with async_session_maker() as session:
        yield session


async def create_db_and_tables():
    """
    Create all tables defined in SQLModel models.
    Call this at application startup after importing all models.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
