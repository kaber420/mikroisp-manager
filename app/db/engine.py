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
from app.core.config import settings
from app.db.resilience import probe_database_connection

# --- Probar conexión antes de inicializar motores ---
# Esto asegura que si Postgres falló en el probe sync, aquí ya usemos SQLite
probe_database_connection()

# --- Database URL Configuration ---
# Read DATABASE_URL from settings
DATABASE_URL = settings.DATABASE_URL


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


async def reload_engine():
    """
    Recarga dinámicamente las configuraciones y recrea el motor SQLAlchemy
    y el sessionmaker sin reiniciar el proceso.
    """
    global engine, async_session_maker
    
    # 1. Volver a instanciar Settings para leer el nuevo data/services.json
    from app.core.config import Settings
    import app.core.config
    
    # Forzar recarga de variables de entorno y archivo services.json
    app.core.config.settings = Settings()
    new_settings = app.core.config.settings
    
    # 2. Ejecutar probe para verificar y activar modo degradado si procede
    from app.db.resilience import probe_database_connection
    probe_database_connection()
    
    # Obtener nueva URL
    new_url = new_settings.DATABASE_URL
    is_sqlite_new = new_url.startswith("sqlite")
    connect_args_new = {"check_same_thread": False} if is_sqlite_new else {}
    
    # Cerrar conexiones previas del motor anterior si es posible
    try:
        await engine.dispose()
    except Exception:
        pass
        
    # 3. Recrear motor
    engine = create_async_engine(new_url, echo=False, connect_args=connect_args_new)
    
    if is_sqlite_new:
        @event.listens_for(engine.sync_engine, "connect", insert=True)
        def set_sqlite_pragma_new(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()
            
    # 4. Recrear session maker
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    print(f"🔄 [Engine Reload] Motor SQLAlchemy recreado con éxito. URL: {new_url.split('@')[-1]}")

