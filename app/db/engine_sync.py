# app/db/engine_sync.py
"""
MOTOR SÍNCRONO - Para toda la aplicación existente.
Este es el engine que usa SQLite de forma síncrona como antes.
Configurado con WAL mode para mejorar concurrencia.
"""
import os
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event
from typing import Generator

# Database path is fixed in data/db/
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create SYNC engine (como antes)
sync_engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)


# Activar WAL mode para mejorar concurrencia y evitar "database is locked"
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()


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
