import logging
import time
import random
from sqlalchemy import create_engine, text
from app.core.config import settings

logger = logging.getLogger(__name__)

def probe_database_connection() -> bool:
    """
    Intenta conectar a la base de datos configurada.
    Implementa un bucle de reintento secuencial (hasta 10 veces cada 5 segundos)
    antes de activar el modo degradado (SQLite).
    """
    # Si ya se forzó SQLite por bandera, no hay nada que probar (sabemos que funciona localmente)
    if settings.IS_FORCED_SQLITE:
        return True

    # Si la URL ya es SQLite, no probamos (se asume segura)
    if settings.DATABASE_URL_SYNC.startswith("sqlite"):
        return True

    db_host_log = settings.DATABASE_URL_SYNC.split("@")[-1]
    
    max_attempts = 10
    base_delay = 1.0
    max_delay = 15.0

    for attempt in range(1, max_attempts + 1):
        logger.info(f"🔍 Probing database connection (Attempt {attempt}/{max_attempts}): {db_host_log}")
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
            logger.warning(f"⚠️ Database connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                # Calcular delay exponencial con jitter (+/- 20%)
                base_backoff = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = random.uniform(-0.2 * base_backoff, 0.2 * base_backoff)
                sleep_interval = max(0.1, base_backoff + jitter)
                logger.info(f"⏳ Retrying in {sleep_interval:.2f} seconds...")
                time.sleep(sleep_interval)
            else:
                logger.critical(f"❌ DATABASE CONNECTION FAILED after {max_attempts} attempts.")

    # Activar MODO DEGRADADO si se agotan los reintentos
    settings.DEGRADED_MODE = True
    
    import os
    from pathlib import Path
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    db_path = Path(DATA_DIR) / "db" / "inventory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    path_str = str(db_path.absolute())
    
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{path_str}"
    settings.DATABASE_URL_SYNC = f"sqlite:///{path_str}"
    
    logger.warning(f"⚠️ FALLBACK: Application starting in DEGRADED MODE using SQLite: {path_str}")
    return False

