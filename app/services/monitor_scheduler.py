import asyncio
import logging
import os
from typing import Dict, List
from datetime import datetime

# New imports
from ..utils.cache import cache_manager
from .router_connector import router_connector

logger = logging.getLogger(__name__)

# Configurable timeout via environment variable (default: 30 seconds)
UNSUBSCRIBE_TIMEOUT = int(os.getenv("MONITOR_UNSUBSCRIBE_TIMEOUT", "30"))
CLEANUP_CHECK_INTERVAL = 10  # Check for expired routers every 10 seconds


class MonitorScheduler:
    """
    Scheduler centralizado que consulta routers suscritos (vía ReadOnly Channel)
    y actualiza el CacheIn-Memory.
    
    Características:
    - 1 conexion persistente por router (gestión por RefCount)
    - Polling paralelo (asyncio.gather)
    - Fallback: Si falla un router, no bloquea a los demás
    - Timeout de desconexión: Espera 30s antes de desconectar si no hay suscriptores
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self._running = False
        self._subscribed_routers: Dict[str, dict] = {}  # host -> {ref_count, last_unsubscribe_time}
        self.poll_interval = poll_interval
        self.UNSUBSCRIBE_TIMEOUT = UNSUBSCRIBE_TIMEOUT
        logger.info(f"[MonitorScheduler] Inicializado (Intervalo: {poll_interval}s, Timeout: {UNSUBSCRIBE_TIMEOUT}s)")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Suscribe un router mediante el RouterConnector.
        Método ASYNC para no bloquear el event loop con la conexión o SSL handshake.
        
        Si el router está marcado para limpieza (ref_count=0), lo reactivamos.
        """
        if host not in self._subscribed_routers:
            self._subscribed_routers[host] = {
                "ref_count": 0,
                "last_unsubscribe_time": None
            }
        
        info = self._subscribed_routers[host]
        was_zero = info["ref_count"] <= 0
        
        info["ref_count"] += 1
        info["last_unsubscribe_time"] = None  # Cancel any pending cleanup
        
        if was_zero:
            logger.info(f"[MonitorScheduler] Resubscribed to {host} (ref_count={info['ref_count']}) - pending cleanup cancelled")
        
        # Delegate connection management to RouterConnector
        try:
            await router_connector.subscribe(host, creds)
            logger.info(f"[MonitorScheduler] Subscribed to {host} (ref_count={info['ref_count']})")
        except Exception as e:
            logger.error(f"[MonitorScheduler] Failed to subscribe to {host}: {e}")
            # Rollback ref_count on failure
            info["ref_count"] -= 1
            if info["ref_count"] <= 0:
                del self._subscribed_routers[host]
            raise

    async def unsubscribe(self, host: str) -> None:
        """
        Desuscribe un router mediante el RouterConnector.
        En lugar de limpiar inmediatamente, marca el router para limpieza
        si ref_count llega a 0. La limpieza ocurrirá después del timeout.
        """
        if host not in self._subscribed_routers:
            return

        info = self._subscribed_routers[host]
        info["ref_count"] -= 1
        
        # Delegate connection release to RouterConnector
        await router_connector.unsubscribe(host)

        if info["ref_count"] <= 0:
            # Mark for cleanup instead of immediate deletion
            info["last_unsubscribe_time"] = datetime.now()
            logger.info(f"[MonitorScheduler] Marked {host} for cleanup in {self.UNSUBSCRIBE_TIMEOUT}s (ref_count=0)")
        else:
            logger.debug(f"[MonitorScheduler] Unsubscribed from {host} (ref_count={info['ref_count']})")

    async def _cleanup_task(self):
        """
        Background task que ejecuta cada 10s para limpiar routers con ref_count=0 > 30s.
        Permite que usuarios que reconectan rápidamente reutilicen la conexión existente.
        """
        logger.info("[MonitorScheduler] Cleanup task started")
        
        while self._running:
            await asyncio.sleep(CLEANUP_CHECK_INTERVAL)
            
            current_time = datetime.now()
            hosts_to_cleanup = []
            
            for host, info in list(self._subscribed_routers.items()):
                if info["ref_count"] <= 0 and info.get("last_unsubscribe_time"):
                    elapsed = (current_time - info["last_unsubscribe_time"]).total_seconds()
                    if elapsed >= self.UNSUBSCRIBE_TIMEOUT:
                        hosts_to_cleanup.append(host)
            
            # Perform cleanup for identified hosts
            for host in hosts_to_cleanup:
                await self._do_cleanup(host)
        
        logger.info("[MonitorScheduler] Cleanup task stopped")

    async def _do_cleanup(self, host: str):
        """
        Ejecuta la limpieza completa de un router:
        - Elimina del diccionario de suscripciones
        - Limpia el cache de stats
        - Limpia las credenciales del connector
        """
        if host not in self._subscribed_routers:
            return
            
        info = self._subscribed_routers[host]
        
        # Double-check: only cleanup if still at ref_count=0
        if info["ref_count"] > 0:
            logger.debug(f"[MonitorScheduler] Skipping cleanup for {host} - ref_count is now {info['ref_count']}")
            return
        
        del self._subscribed_routers[host]
        
        # Clean up cache
        cache_manager.get_store("router_stats").delete(host)
        
        # Clean up credentials in connector
        router_connector.cleanup_credentials(host)
        
        logger.info(f"[MonitorScheduler] Fully unsubscribed from {host} (timeout expired)")

    async def run(self):
        """Loop principal Async."""
        self._running = True
        logger.info("[MonitorScheduler] Iniciando loop de polling...")
        
        # Start cleanup task in parallel
        cleanup_task = asyncio.create_task(self._cleanup_task())
        
        # Cache store para stats
        stats_cache = cache_manager.get_store("router_stats", default_ttl=5)

        try:
            while self._running:
                # Copia para iterar seguro
                targets = list(self._subscribed_routers.items())
                
                if not targets:
                    await asyncio.sleep(1)
                    continue
                
                # Filter: only poll routers with active subscribers (ref_count > 0)
                active_targets = [(host, info) for host, info in targets if info["ref_count"] > 0]
                
                if not active_targets:
                    await asyncio.sleep(1)
                    continue
                
                # Crear tareas de polling paralelo
                tasks = []
                for host, info in active_targets:
                    tasks.append(self._poll_host(host))
                
                # Ejecutar todas (paralelismo real I/O)
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar resultados
                for (host, _), result in zip(active_targets, results):
                    if isinstance(result, Exception):
                        logger.error(f"[MonitorScheduler] Error polling {host}: {result}")
                        stats_cache.set(host, {"error": str(result)})
                    elif result:
                        # Guardar en cache
                        stats_cache.set(host, result)

                await asyncio.sleep(self.poll_interval)
        finally:
            # Ensure cleanup task is cancelled when main loop stops
            self._running = False
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
        logger.info("[MonitorScheduler] Detenido.")

    async def _poll_host(self, host: str) -> dict:
        """
        Ejecuta la consulta al API mediante RouterConnector.
        Usa run_in_executor para no bloquear el loop principal con RLock o llamadas síncronas.
        """
        return await asyncio.to_thread(router_connector.fetch_router_stats, host)


# Singleton
monitor_scheduler = MonitorScheduler()
