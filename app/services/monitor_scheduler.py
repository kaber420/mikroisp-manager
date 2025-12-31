import asyncio
import logging
from typing import Dict, List
from datetime import datetime

# New imports
from ..utils.cache import cache_manager
from .router_connector import router_connector

logger = logging.getLogger(__name__)

class MonitorScheduler:
    """
    Scheduler centralizado que consulta routers suscritos (vía ReadOnly Channel)
    y actualiza el CacheIn-Memory.
    
    Características:
    - 1 conexion persistente por router (gestión por RefCount)
    - Polling paralelo (asyncio.gather)
    - Fallback: Si falla un router, no bloquea a los demás
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self._running = False
        self._subscribed_routers: Dict[str, dict] = {} # host -> creds
        self.poll_interval = poll_interval
        logger.info(f"[MonitorScheduler] Inicializado (Intervalo: {poll_interval}s)")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Suscribe un router mediante el RouterConnector.
        Método ASYNC para no bloquear el event loop con la conexión o SSL handshake.
        """
        if host not in self._subscribed_routers:
            self._subscribed_routers[host] = {"ref_count": 0}
        
        self._subscribed_routers[host]["ref_count"] += 1
        
        # Delegate connection management to RouterConnector
        try:
            await router_connector.subscribe(host, creds)
        except Exception as e:
            logger.error(f"[MonitorScheduler] Failed to subscribe to {host}: {e}")
            # Rollback ref_count on failure
            self._subscribed_routers[host]["ref_count"] -= 1
            if self._subscribed_routers[host]["ref_count"] <= 0:
                del self._subscribed_routers[host]
            raise

    async def unsubscribe(self, host: str) -> None:
        """
        Desuscribe un router mediante el RouterConnector.
        Método ASYNC para no bloquear si hay que cerrar socket.
        """
        if host not in self._subscribed_routers:
            return

        self._subscribed_routers[host]["ref_count"] -= 1
        
        # Delegate connection release to RouterConnector
        await router_connector.unsubscribe(host)

        if self._subscribed_routers[host]["ref_count"] <= 0:
            del self._subscribed_routers[host]
            # Limpiamos cache también
            cache_manager.get_store("router_stats").delete(host)
            # Coordinated cleanup: tell connector to remove credentials
            router_connector.cleanup_credentials(host)
            logger.info(f"[MonitorScheduler] Fully unsubscribed from {host} (ref_count=0)")

    async def run(self):
        """Loop principal Async."""
        self._running = True
        logger.info("[MonitorScheduler] Iniciando loop de polling...")
        
        # Cache store para stats
        stats_cache = cache_manager.get_store("router_stats", default_ttl=5)

        while self._running:
            # Copia para iterar seguro
            targets = list(self._subscribed_routers.items())
            
            if not targets:
                await asyncio.sleep(1)
                continue
            
            # Crear tareas de polling paralelo
            tasks = []
            for host, info in targets:
                tasks.append(self._poll_host(host))
            
            # Ejecutar todas (paralelismo real I/O)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            for host, result in zip([t[0] for t in targets], results):
                if isinstance(result, Exception):
                    logger.error(f"[MonitorScheduler] Error polling {host}: {result}")
                    stats_cache.set(host, {"error": str(result)})
                elif result:
                    # Guardar en cache
                    stats_cache.set(host, result)

            await asyncio.sleep(self.poll_interval)
            
        logger.info("[MonitorScheduler] Detenido.")

    async def _poll_host(self, host: str) -> dict:
        """
        Ejecuta la consulta al API mediante RouterConnector.
        Usa run_in_executor para no bloquear el loop principal con RLock o llamadas síncronas.
        """
        return await asyncio.to_thread(router_connector.fetch_router_stats, host)

# Singleton
monitor_scheduler = MonitorScheduler()
