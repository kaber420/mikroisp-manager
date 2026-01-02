# app/services/ap_monitor_scheduler.py
"""
APMonitorScheduler: Scheduler centralizado para polling de APs.
Análogo a MonitorScheduler pero para dispositivos AP multi-vendor.
"""

import asyncio
import logging
import os
from typing import Dict
from datetime import datetime

from ..utils.cache import cache_manager
from .ap_connector import ap_connector
from ..db import aps_db

logger = logging.getLogger(__name__)

# Configurable timeout via environment variable (default: 30 seconds)
UNSUBSCRIBE_TIMEOUT = int(os.getenv("AP_MONITOR_UNSUBSCRIBE_TIMEOUT", "30"))
CLEANUP_CHECK_INTERVAL = 10  # Check for expired APs every 10 seconds
DEFAULT_POLL_INTERVAL = 2  # Default polling interval in seconds


class APMonitorScheduler:
    """Scheduler centralizado: polling paralelo a APs con timeout de desconexión."""
    
    def __init__(self, poll_interval: float = 2.0):
        self._running = False
        self._subscribed_aps: Dict[str, dict] = {}  # host -> {ref_count, last_unsubscribe_time, interval}
        self.poll_interval = poll_interval
        self.UNSUBSCRIBE_TIMEOUT = UNSUBSCRIBE_TIMEOUT
        logger.info(f"[APMonitorScheduler] Inicializado (Intervalo: {poll_interval}s, Timeout: {UNSUBSCRIBE_TIMEOUT}s)")
    
    async def subscribe(self, host: str, creds: dict, interval: int = None) -> None:
        """
        Suscribe un AP. Si está marcado para limpieza, lo reactiva.
        
        Args:
            host: AP hostname/IP
            creds: Dictionary with username, password, vendor, port
            interval: Optional per-AP polling interval
        """
        if host not in self._subscribed_aps:
            self._subscribed_aps[host] = {
                "ref_count": 0,
                "last_unsubscribe_time": None,
                "interval": interval or DEFAULT_POLL_INTERVAL
            }
        
        info = self._subscribed_aps[host]
        was_zero = info["ref_count"] <= 0
        
        info["ref_count"] += 1
        info["last_unsubscribe_time"] = None  # Cancel any pending cleanup
        
        if interval:
            info["interval"] = interval
        
        if was_zero:
            logger.info(f"[APMonitorScheduler] Resubscribed to {host} (ref_count={info['ref_count']}) - pending cleanup cancelled")
        
        try:
            await ap_connector.subscribe(host, creds)
            logger.info(f"[APMonitorScheduler] Subscribed to {host} (ref_count={info['ref_count']})")
        except Exception as e:
            logger.error(f"[APMonitorScheduler] Failed to subscribe to {host}: {e}")
            info["ref_count"] -= 1
            if info["ref_count"] <= 0:
                del self._subscribed_aps[host]
            raise

    async def unsubscribe(self, host: str) -> None:
        """Desuscribe un AP. Si ref_count=0, marca para limpieza con timeout."""
        if host not in self._subscribed_aps:
            return

        info = self._subscribed_aps[host]
        info["ref_count"] -= 1
        await ap_connector.unsubscribe(host)

        if info["ref_count"] <= 0:
            info["last_unsubscribe_time"] = datetime.now()
            logger.info(f"[APMonitorScheduler] Marked {host} for cleanup in {self.UNSUBSCRIBE_TIMEOUT}s (ref_count=0)")
        else:
            logger.debug(f"[APMonitorScheduler] Unsubscribed from {host} (ref_count={info['ref_count']})")

    async def _cleanup_task(self):
        """Limpia APs inactivos después del timeout."""
        logger.info("[APMonitorScheduler] Cleanup task started")
        
        while self._running:
            await asyncio.sleep(CLEANUP_CHECK_INTERVAL)
            
            current_time = datetime.now()
            hosts_to_cleanup = []
            
            for host, info in list(self._subscribed_aps.items()):
                if info["ref_count"] <= 0 and info.get("last_unsubscribe_time"):
                    elapsed = (current_time - info["last_unsubscribe_time"]).total_seconds()
                    if elapsed >= self.UNSUBSCRIBE_TIMEOUT:
                        hosts_to_cleanup.append(host)
            
            for host in hosts_to_cleanup:
                await self._do_cleanup(host)
        
        logger.info("[APMonitorScheduler] Cleanup task stopped")

    async def _do_cleanup(self, host: str):
        """Limpia suscripciones, cache y credenciales de un AP."""
        if host not in self._subscribed_aps:
            return
            
        info = self._subscribed_aps[host]
        if info["ref_count"] > 0:
            logger.debug(f"[APMonitorScheduler] Skipping cleanup for {host} - ref_count is now {info['ref_count']}")
            return
        
        del self._subscribed_aps[host]
        cache_manager.get_store("ap_stats").delete(host)
        ap_connector.cleanup(host)
        
        logger.info(f"[APMonitorScheduler] Fully unsubscribed from {host} (timeout expired)")

    async def _update_db_status(self, host: str, status: str, result: dict = None):
        """Actualiza el estado del AP en la base de datos."""
        try:
            await asyncio.to_thread(aps_db.update_ap_status, host, status, result)
            logger.debug(f"[APMonitorScheduler] DB updated: {host} -> {status}")
        except Exception as e:
            logger.error(f"[APMonitorScheduler] Failed to update DB for {host}: {e}")

    async def refresh_host(self, host: str) -> dict:
        """
        Realiza un poll inmediato al AP y actualiza DB + cache.
        Útil después de crear un AP para mostrar 'Online' inmediatamente.
        """
        stats_cache = cache_manager.get_store("ap_stats", default_ttl=5)
        
        try:
            result = await self._poll_host(host)
            if result and "error" not in result:
                stats_cache.set(host, result)
                await self._update_db_status(host, "online", result)
                return result
            else:
                await self._update_db_status(host, "offline")
                return result or {"error": "No data returned"}
        except Exception as e:
            logger.error(f"[APMonitorScheduler] refresh_host failed for {host}: {e}")
            await self._update_db_status(host, "offline")
            return {"error": str(e)}

    async def run(self):
        """Loop principal Async."""
        self._running = True
        logger.info("[APMonitorScheduler] Iniciando loop de polling...")
        cleanup_task = asyncio.create_task(self._cleanup_task())
        stats_cache = cache_manager.get_store("ap_stats", default_ttl=5)

        try:
            while self._running:
                targets = list(self._subscribed_aps.items())
                
                if not targets:
                    await asyncio.sleep(1)
                    continue
                
                active_targets = [(host, info) for host, info in targets if info["ref_count"] > 0]
                
                if not active_targets:
                    await asyncio.sleep(1)
                    continue
                
                tasks = [self._poll_host(host) for host, _ in active_targets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (host, _), result in zip(active_targets, results):
                    if isinstance(result, Exception):
                        logger.error(f"[APMonitorScheduler] Error polling {host}: {result}")
                        stats_cache.set(host, {"error": str(result)})
                        await self._update_db_status(host, "offline")
                    elif result and "error" not in result:
                        stats_cache.set(host, result)
                        await self._update_db_status(host, "online", result)
                    elif result:
                        stats_cache.set(host, result)
                        await self._update_db_status(host, "offline")

                await asyncio.sleep(self.poll_interval)
        finally:
            self._running = False
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
        logger.info("[APMonitorScheduler] Detenido.")

    async def _poll_host(self, host: str) -> dict:
        """Ejecuta la consulta al AP en un thread separado."""
        return await asyncio.to_thread(ap_connector.fetch_ap_stats, host)


# Singleton
ap_monitor_scheduler = APMonitorScheduler()
