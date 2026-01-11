import asyncio
import logging
import os
from typing import Dict, List
from datetime import datetime, timedelta

from ..utils.cache import cache_manager
from .router_connector import router_connector
from ..db import router_db
from ..db.stats_db import save_router_monitor_stats

logger = logging.getLogger(__name__)

# Configurable timeout via environment variable (default: 30 seconds)
UNSUBSCRIBE_TIMEOUT = int(os.getenv("MONITOR_UNSUBSCRIBE_TIMEOUT", "30"))
CLEANUP_CHECK_INTERVAL = 10  # Check for expired routers every 10 seconds
# Interval for saving router stats to history (default: 5 minutes)
ROUTER_HISTORY_INTERVAL = int(os.getenv("ROUTER_HISTORY_INTERVAL", "300"))


class MonitorScheduler:
    """Scheduler centralizado: polling paralelo a routers con timeout de desconexión."""
    
    def __init__(self, poll_interval: float = 2.0):
        self._running = False
        self._subscribed_routers: Dict[str, dict] = {}  # host -> {ref_count, last_unsubscribe_time}
        self.poll_interval = poll_interval
        self.UNSUBSCRIBE_TIMEOUT = UNSUBSCRIBE_TIMEOUT
        logger.info(f"[MonitorScheduler] Inicializado (Intervalo: {poll_interval}s, Timeout: {UNSUBSCRIBE_TIMEOUT}s)")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """Suscribe un router. Si está marcado para limpieza, lo reactiva."""
        if host not in self._subscribed_routers:
            self._subscribed_routers[host] = {
                "ref_count": 0,
                "last_unsubscribe_time": None,
                "last_history_save": None,
                "backoff_until": None,  # Backoff exponencial para errores
                "consecutive_failures": 0
            }
        
        info = self._subscribed_routers[host]
        
        # Check backoff: si hubo error reciente, no intentar reconectar aún
        if info.get("backoff_until"):
            elapsed = (datetime.now() - info["backoff_until"]).total_seconds()
            if elapsed < 0:
                logger.warning(f"[MonitorScheduler] Skipping subscribe to {host} - in backoff ({-elapsed:.0f}s remaining)")
                raise Exception(f"Router {host} en período de espera por errores previos")
        
        was_zero = info["ref_count"] <= 0
        
        info["ref_count"] += 1
        info["last_unsubscribe_time"] = None  # Cancel any pending cleanup
        
        if was_zero:
            logger.info(f"[MonitorScheduler] Resubscribed to {host} (ref_count={info['ref_count']}) - pending cleanup cancelled")
        
        try:
            await router_connector.subscribe(host, creds)
            # Conexión exitosa: resetear backoff
            info["consecutive_failures"] = 0
            info["backoff_until"] = None
            logger.info(f"[MonitorScheduler] Subscribed to {host} (ref_count={info['ref_count']})")
        except Exception as e:
            # Sanitize error message to hide passwords
            error_msg = str(e)
            if "password=" in error_msg:
                import re
                # Mask value in password=... pattern (case insensitive)
                error_msg = re.sub(r'password=[^ \t\n\r\f\v]+"?', 'password=******', error_msg, flags=re.IGNORECASE)
                
            logger.error(f"[MonitorScheduler] Failed to subscribe to {host}: {error_msg}")
            info["ref_count"] -= 1
            # Aplicar backoff exponencial (5s, 10s, 20s, 40s, max 60s)
            info["consecutive_failures"] = info.get("consecutive_failures", 0) + 1
            backoff_seconds = min(5 * (2 ** (info["consecutive_failures"] - 1)), 60)
            info["backoff_until"] = datetime.now() + timedelta(seconds=backoff_seconds)
            logger.warning(f"[MonitorScheduler] Backoff for {host}: {backoff_seconds}s (failures: {info['consecutive_failures']})")
            
            if info["ref_count"] <= 0:
                del self._subscribed_routers[host]
            # Don't raise the raw exception with password either - raise a sanitized one or just the class
            raise Exception(error_msg)

    async def unsubscribe(self, host: str) -> None:
        """Desuscribe un router. Si ref_count=0, marca para limpieza con timeout."""
        if host not in self._subscribed_routers:
            return

        info = self._subscribed_routers[host]
        info["ref_count"] -= 1
        await router_connector.unsubscribe(host)

        if info["ref_count"] <= 0:
            info["last_unsubscribe_time"] = datetime.now()
            logger.info(f"[MonitorScheduler] Marked {host} for cleanup in {self.UNSUBSCRIBE_TIMEOUT}s (ref_count=0)")
        else:
            logger.debug(f"[MonitorScheduler] Unsubscribed from {host} (ref_count={info['ref_count']})")

    async def _cleanup_task(self):
        """Limpia routers inactivos después del timeout."""
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
            
            for host in hosts_to_cleanup:
                await self._do_cleanup(host)
        
        logger.info("[MonitorScheduler] Cleanup task stopped")

    async def _do_cleanup(self, host: str):
        """Limpia suscripciones, cache y credenciales de un router."""
        if host not in self._subscribed_routers:
            return
            
        info = self._subscribed_routers[host]
        if info["ref_count"] > 0:
            logger.debug(f"[MonitorScheduler] Skipping cleanup for {host} - ref_count is now {info['ref_count']}")
            return
        
        del self._subscribed_routers[host]
        cache_manager.get_store("router_stats").delete(host)
        router_connector.cleanup_credentials(host)
        
        logger.info(f"[MonitorScheduler] Fully unsubscribed from {host} (timeout expired)")

    async def _update_db_status(self, host: str, status: str, result: dict = None):
        """Actualiza el estado del router en la base de datos."""
        try:
            await asyncio.to_thread(router_db.update_router_status, host, status, result)
            logger.debug(f"[MonitorScheduler] DB updated: {host} -> {status}")
        except Exception as e:
            logger.error(f"[MonitorScheduler] Failed to update DB for {host}: {e}")

    def reset_connection(self, host: str) -> dict:
        """
        Resetea el estado de conexión de un router (backoff, errores, etc.)
        sin eliminarlo ni perder su configuración.
        
        Útil para recuperar un router que entró en estado de error.
        
        Returns:
            dict con status y mensaje
        """
        # 1. Limpiar estado en el scheduler
        if host in self._subscribed_routers:
            info = self._subscribed_routers[host]
            info["backoff_until"] = None
            info["consecutive_failures"] = 0
            info["last_unsubscribe_time"] = None
            logger.info(f"[MonitorScheduler] Reset backoff state for {host}")
        
        # 2. Limpiar caché de stats
        try:
            stats_cache = cache_manager.get_store("router_stats")
            stats_cache.delete(host)
            logger.info(f"[MonitorScheduler] Cleared stats cache for {host}")
        except Exception as e:
            logger.warning(f"[MonitorScheduler] Could not clear cache for {host}: {e}")
        
        # 3. Limpiar pool de conexiones del router
        try:
            from ..utils.device_clients.mikrotik import connection as mikrotik_conn
            mikrotik_conn.remove_pool(host)
            logger.info(f"[MonitorScheduler] Cleared connection pool for {host}")
        except Exception as e:
            logger.warning(f"[MonitorScheduler] Could not clear pool for {host}: {e}")
        
        # 4. Limpiar credenciales del connector (forzará re-autenticación)
        try:
            router_connector.cleanup_credentials(host)
            logger.info(f"[MonitorScheduler] Cleared credentials for {host}")
        except Exception as e:
            logger.warning(f"[MonitorScheduler] Could not clear credentials for {host}: {e}")
        
        return {
            "status": "success",
            "message": f"Estado de conexión reseteado para {host}. Listo para reconectar."
        }

    async def refresh_host(self, host: str) -> dict:
        """
        Realiza un poll inmediato al router y actualiza DB + cache.
        Útil después de provisionar para mostrar 'Online' inmediatamente.
        """
        stats_cache = cache_manager.get_store("router_stats", default_ttl=5)
        
        try:
            result = await self._poll_host(host)
            if result:
                stats_cache.set(host, result)
                await self._update_db_status(host, "online", result)
                return result
            else:
                await self._update_db_status(host, "offline")
                return {"error": "No data returned"}
        except Exception as e:
            logger.error(f"[MonitorScheduler] refresh_host failed for {host}: {e}")
            await self._update_db_status(host, "offline")
            return {"error": str(e)}

    async def run(self):
        """Loop principal Async."""
        self._running = True
        logger.info("[MonitorScheduler] Iniciando loop de polling...")
        cleanup_task = asyncio.create_task(self._cleanup_task())
        stats_cache = cache_manager.get_store("router_stats", default_ttl=5)

        try:
            while self._running:
                targets = list(self._subscribed_routers.items())
                
                if not targets:
                    await asyncio.sleep(1)
                    continue
                
                active_targets = [(host, info) for host, info in targets if info["ref_count"] > 0]
                
                if not active_targets:
                    await asyncio.sleep(1)
                    continue
                
                tasks = [self._poll_host(host) for host, _ in active_targets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                current_time = datetime.now()
                for (host, info), result in zip(active_targets, results):
                    if isinstance(result, Exception):
                        logger.error(f"[MonitorScheduler] Error polling {host}: {result}")
                        stats_cache.set(host, {"error": str(result)})
                        await self._update_db_status(host, "offline")
                    elif result:
                        stats_cache.set(host, result)
                        await self._update_db_status(host, "online", result)
                        
                        # Save to history if enough time has passed
                        last_save = info.get("last_history_save")
                        if last_save is None or (current_time - last_save).total_seconds() >= ROUTER_HISTORY_INTERVAL:
                            try:
                                await asyncio.to_thread(save_router_monitor_stats, host, result)
                                info["last_history_save"] = current_time
                                logger.debug(f"[MonitorScheduler] Saved history for {host}")
                            except Exception as e:
                                logger.error(f"[MonitorScheduler] Failed to save history for {host}: {e}")

                await asyncio.sleep(self.poll_interval)
        finally:
            self._running = False
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
        logger.info("[MonitorScheduler] Detenido.")

    async def _poll_host(self, host: str) -> dict:
        """Ejecuta la consulta al router en un thread separado."""
        return await asyncio.to_thread(router_connector.fetch_router_stats, host)


# Singleton
monitor_scheduler = MonitorScheduler()
