# app/db/engine.py
"""
SQLModel database engine and session management for FastAPI Users integration.
Uses AsyncSession for compatibility with fastapi-users-db-sqlalchemy.
Supports SQLite (default) and PostgreSQL via DATABASE_URL environment variable.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# --- Database URL Configuration ---
# Read DATABASE_URL from environment. If not set, default to SQLite.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    # Default to SQLite in data/db/
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
    os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"

# Detect dialect from URL
_is_sqlite = DATABASE_URL.startswith("sqlite")

# Create async engine with appropriate connect_args
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


# Activate WAL mode only for SQLite to improve concurrency
if _is_sqlite:
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
