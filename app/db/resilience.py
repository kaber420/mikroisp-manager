import logging
import time
from sqlalchemy import create_engine, text
from app.core.config import settings

logger = logging.getLogger(__name__)

def probe_database_connection() -> bool:
    """
    Intenta conectar a la base de datos configurada.
    Si falla y no es SQLite, activa el modo degradado y cambia a SQLite.
    """
    # Si ya se forzó SQLite por bandera, no hay nada que probar (sabemos que funciona localmente)
    if settings.IS_FORCED_SQLITE:
        return True

    # Si la URL ya es SQLite, no probamos (se asume segura)
    if settings.DATABASE_URL_SYNC.startswith("sqlite"):
        return True

    logger.info(f"🔍 Probing database connection: {settings.DATABASE_URL_SYNC.split('@')[-1]}") # Loguear host sin credenciales
    
    try:
        # Intentar crear un motor temporal con timeout agresivo
        temp_engine = create_engine(
            settings.DATABASE_URL_SYNC, 
            connect_args={"connect_timeout": 3} if "postgres" in settings.DATABASE_URL_SYNC else {}
        )
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return True
    except Exception as e:
        logger.critical(f"❌ DATABASE CONNECTION FAILED: {e}")
        
        # Activar MODO DEGRADADO
        settings.DEGRADED_MODE = True
        
        # Reconfigurar URLs a SQLite de emergencia
        import os
        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
        
        settings.DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"
        settings.DATABASE_URL_SYNC = f"sqlite:///{DATABASE_FILE}"
        
        logger.warning(f"⚠️ FALLBACK: Application starting in DEGRADED MODE using SQLite: {DATABASE_FILE}")
        return False
