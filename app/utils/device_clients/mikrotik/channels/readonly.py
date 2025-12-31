from threading import RLock
from typing import Dict
from routeros_api import RouterOsApiPool
import logging

logger = logging.getLogger(__name__)

class ReadOnlyChannelManager:
    """
    Gestiona conexiones de solo lectura para monitoreo persistente.
    Usa Reference Counting para cerrar conexiones cuando no hay suscriptores.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._channels = {}
            cls._instance._ref_counts = {}
            cls._instance._lock = RLock()
        return cls._instance
    
    def acquire(self, host: str, username: str, password: str, port: int = 8729):
        """
        Obtiene o crea un canal de lectura. Incrementa ref count.
        """
        key = f"{host}:{port}"
        
        with self._lock:
            # Check if pool exists and is connected
            if key not in self._channels:
                logger.info(f"[ReadOnlyChannel] Creando conexión persistente para {host}")
                self._channels[key] = self._create_pool(host, username, password, port)
                self._ref_counts[key] = 0
            
            self._ref_counts[key] += 1
            logger.debug(f"[ReadOnlyChannel] {host} ref_count={self._ref_counts[key]}")
            
            try:
                return self._channels[key].get_api()
            except Exception as e:
                # If get_api fails, maybe connection died. Clear and retry once.
                logger.warning(f"[ReadOnlyChannel] Error obteniendo API para {host}: {e}. Retrying.")
                self._force_disconnect(key)
                self._channels[key] = self._create_pool(host, username, password, port)
                return self._channels[key].get_api()

    def release(self, host: str, port: int = 8729):
        """
        Libera referencia. Si llega a 0, cierra la conexión.
        """
        key = f"{host}:{port}"
        
        with self._lock:
            if key in self._ref_counts:
                self._ref_counts[key] -= 1
                logger.debug(f"[ReadOnlyChannel] {host} ref_count={self._ref_counts[key]}")
                
                if self._ref_counts[key] <= 0:
                    self._force_disconnect(key)
                    if key in self._ref_counts:
                        del self._ref_counts[key]

    def _force_disconnect(self, key: str):
        if key in self._channels:
            try:
                self._channels[key].disconnect()
                logger.info(f"[ReadOnlyChannel] Conexión cerrada para {key}")
            except Exception as e:
                logger.error(f"[ReadOnlyChannel] Error cerrando {key}: {e}")
            del self._channels[key]

    def _create_pool(self, host, username, password, port):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        return RouterOsApiPool(
            host, username=username, password=password,
            port=port, use_ssl=True, ssl_context=ssl_context,
            plaintext_login=True
        )

# Singleton global
readonly_channels = ReadOnlyChannelManager()
