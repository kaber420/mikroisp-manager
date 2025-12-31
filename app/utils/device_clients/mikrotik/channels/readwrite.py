import ssl
from routeros_api import RouterOsApiPool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_config_channel(host: str, username: str, password: str, port: int = 8729):
    """
    Context manager para operaciones de escritura / config.
    Abre conexión, entrega API, y cierra automáticamente al salir.
    ESTRICTAMENTE ONE-SHOT.
    """
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    pool = RouterOsApiPool(
        host, username=username, password=password,
        port=port, use_ssl=True, ssl_context=ssl_context,
        plaintext_login=True
    )
    
    try:
        api = pool.get_api()
        yield api
    except Exception as e:
        logger.error(f"[ConfigChannel] Error en operación config {host}: {e}")
        raise
    finally:
        try:
            pool.disconnect()
        except:
            pass
