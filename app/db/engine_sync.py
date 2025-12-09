# app/db/engine_sync.py
"""
MOTOR SÍNCRONO - Para toda la aplicación existente.
Este es el engine que usa SQLite de forma síncrona como antes.
"""
import os
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

# Read database path from environment or use default
DATABASE_FILE = os.getenv("INVENTORY_DB_FILE", "inventory.sqlite")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create SYNC engine (como antes)
sync_engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)


def get_sync_session() -> Generator[Session, None, None]:
    """
    Dependency for SYNC SQLModel session injection.
    Usa esto en TODA tu aplicación existente (routers, billing, monitor, etc.)
    """
    with Session(sync_engine) as session:
        yield session


def create_sync_db_and_tables():
    """
    Create all tables with SYNC engine.
    Para crear tablas de forma síncrona.
    """
    SQLModel.metadata.create_all(sync_engine)
