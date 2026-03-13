import time
import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def test_postgres_connection(host: str, port: int, user: str, password: str, db: str) -> dict:
    """
    Prueba conectividad a PostgreSQL sincrónicamente con timeout rápido.
    No afecta al motor principal.
    """
    # Usamos psycopg ya que es el driver estándar en este proyecto
    if password:
        url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    else:
        url = f"postgresql+psycopg://{user}@{host}:{port}/{db}"
    
    start = time.time()
    try:
        # Timeout agresivo para no bloquear la UI
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = int((time.time() - start) * 1000)
        return {"ok": True, "latency_ms": latency, "error": None}
    except Exception as e:
        return {"ok": False, "latency_ms": 0, "error": str(e)}

def test_sqlite_connection() -> dict:
    """
    Prueba conectividad a SQLite (comprueba si puede crear/acceder al archivo).
    """
    import os
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
    os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
    url = f"sqlite:///{DATABASE_FILE}"
    
    start = time.time()
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = int((time.time() - start) * 1000)
        return {"ok": True, "latency_ms": latency, "error": None}
    except Exception as e:
        return {"ok": False, "latency_ms": 0, "error": str(e)}


def test_redict_connection(host: str, port: int, password: str, db: int) -> dict:
    """
    Prueba conectividad a Redict/Redis sincrónicamente.
    """
    # Importar sincrónico normal de redis
    try:
        import redis
    except ImportError:
        return {"ok": False, "latency_ms": 0, "error": "Redis library not installed"}
        
    auth = f":{password}@" if password else ""
    # Evitar url con "::" si no hay password pero se requiere estructura, from_url asume bien el formato standard
    url = f"redis://{auth}{host}:{port}/{db}"
    
    start = time.time()
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=3.0)
        client.ping()
        latency = int((time.time() - start) * 1000)
        return {"ok": True, "latency_ms": latency, "error": None}
    except Exception as e:
        return {"ok": False, "latency_ms": 0, "error": str(e)}

def test_memory_cache_connection() -> dict:
    """
    Simulación de test para Memory Cache (siempre responde okay si la ram existe).
    """
    return {"ok": True, "latency_ms": 1, "error": None}
