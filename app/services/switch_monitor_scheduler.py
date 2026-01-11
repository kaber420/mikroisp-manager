import asyncio
import logging
import os
from typing import Dict
from datetime import datetime

from ..utils.cache import cache_manager
from .switch_connector import switch_connector
from ..db import switches_db

logger = logging.getLogger(__name__)

# Configurable timeout via environment variable (default: 30 seconds)
UNSUBSCRIBE_TIMEOUT = int(os.getenv("SWITCH_MONITOR_UNSUBSCRIBE_TIMEOUT", "30"))
CLEANUP_CHECK_INTERVAL = 10
SWITCH_HISTORY_INTERVAL = int(os.getenv("SWITCH_HISTORY_INTERVAL", "300"))


class SwitchMonitorScheduler:
    """Scheduler centralizado: polling paralelo a switches con timeout de desconexión."""
    
    def __init__(self, poll_interval: float = 5.0):
        self._running = False
        self._subscribed_switches: Dict[str, dict] = {}  # host -> {ref_count, last_unsubscribe_time}
        self.poll_interval = poll_interval
        self.UNSUBSCRIBE_TIMEOUT = UNSUBSCRIBE_TIMEOUT
        logger.info(f"[SwitchMonitorScheduler] Initialized (Interval: {poll_interval}s)")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """Subscribe a switch. Resets cleanup timer if pending."""
        if host not in self._subscribed_switches:
            self._subscribed_switches[host] = {
                "ref_count": 0,
                "last_unsubscribe_time": None
            }
        
        info = self._subscribed_switches[host]
        was_zero = info["ref_count"] <= 0
        
        info["ref_count"] += 1
        info["last_unsubscribe_time"] = None
        
        if was_zero:
            logger.info(f"[SwitchMonitorScheduler] Resubscribed to {host} - cleanup cancelled")
        
        try:
            await switch_connector.subscribe(host, creds)
            logger.info(f"[SwitchMonitorScheduler] Subscribed to {host} (ref_count={info['ref_count']})")
            
            # Immediate poll to populate cache right away
            await self.refresh_host(host)
            
        except Exception as e:
            logger.error(f"[SwitchMonitorScheduler] Failed to subscribe to {host}: {e}")
            info["ref_count"] -= 1
            if info["ref_count"] <= 0:
                del self._subscribed_switches[host]
            raise

    async def refresh_host(self, host: str) -> dict:
        """
        Immediate poll to populate cache. Called after subscribe.
        """
        stats_cache = cache_manager.get_store("switch_stats", default_ttl=10)
        
        try:
            result = await self._poll_host(host)
            if result and "error" not in result:
                stats_cache.set(host, result)
                await self._update_db_status(host, "online", result)
                logger.info(f"[SwitchMonitorScheduler] Immediate poll success for {host}")
                return result
            else:
                stats_cache.set(host, result or {"error": "No data"})
                await self._update_db_status(host, "offline")
                return result or {"error": "No data"}
        except Exception as e:
            logger.error(f"[SwitchMonitorScheduler] refresh_host failed for {host}: {e}")
            stats_cache.set(host, {"error": str(e)})
            await self._update_db_status(host, "offline")
            return {"error": str(e)}

    async def unsubscribe(self, host: str) -> None:
        """Unsubscribe a switch. Marks for cleanup if ref_count is 0."""
        if host not in self._subscribed_switches:
            return

        info = self._subscribed_switches[host]
        info["ref_count"] -= 1
        await switch_connector.unsubscribe(host)

        if info["ref_count"] <= 0:
            info["last_unsubscribe_time"] = datetime.now()
            logger.info(f"[SwitchMonitorScheduler] Marked {host} for cleanup in {self.UNSUBSCRIBE_TIMEOUT}s")
        else:
            logger.debug(f"[SwitchMonitorScheduler] Unsubscribed from {host} (ref_count={info['ref_count']})")

    async def _cleanup_task(self):
        """Cleanup inactive switches."""
        logger.info("[SwitchMonitorScheduler] Cleanup task started")
        
        while self._running:
            await asyncio.sleep(CLEANUP_CHECK_INTERVAL)
            
            current_time = datetime.now()
            hosts_to_cleanup = []
            
            for host, info in list(self._subscribed_switches.items()):
                if info["ref_count"] <= 0 and info.get("last_unsubscribe_time"):
                    elapsed = (current_time - info["last_unsubscribe_time"]).total_seconds()
                    if elapsed >= self.UNSUBSCRIBE_TIMEOUT:
                        hosts_to_cleanup.append(host)
            
            for host in hosts_to_cleanup:
                await self._do_cleanup(host)

    async def _do_cleanup(self, host: str):
        """Perform cleanup."""
        if host not in self._subscribed_switches:
            return
            
        info = self._subscribed_switches[host]
        if info["ref_count"] > 0:
            return
        
        del self._subscribed_switches[host]
        cache_manager.get_store("switch_stats").delete(host)
        switch_connector.cleanup_credentials(host)
        
        logger.info(f"[SwitchMonitorScheduler] Fully unsubscribed from {host}")

    async def _update_db_status(self, host: str, status: str, result: dict = None):
        """Update switch status in DB."""
        try:
            # Note: Assuming switches_db has this method, similar to router_db
            # If not, we might need to add it or use update_switch_in_db
            update_data = {"last_status": status}
            if result:
                 update_data.update({
                     "hostname": result.get("name") or result.get("hostname"),
                     "model": result.get("board_name"),
                     "firmware": result.get("version")
                 })
            
            await asyncio.to_thread(switches_db.update_switch_in_db, host, update_data)
        except Exception as e:
            logger.error(f"[SwitchMonitorScheduler] Failed to update DB for {host}: {e}")

    async def run(self):
        """Main periodic polling loop."""
        self._running = True
        logger.info("[SwitchMonitorScheduler] Starting polling loop...")
        cleanup_task = asyncio.create_task(self._cleanup_task())
        stats_cache = cache_manager.get_store("switch_stats", default_ttl=10)

        try:
            while self._running:
                targets = list(self._subscribed_switches.items())
                active_targets = [(host, info) for host, info in targets if info["ref_count"] > 0]
                
                if not active_targets:
                    await asyncio.sleep(1)
                    continue
                
                tasks = [self._poll_host(host) for host, _ in active_targets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (host, info), result in zip(active_targets, results):
                    if isinstance(result, Exception):
                        logger.error(f"[SwitchMonitorScheduler] Error polling {host}: {result}")
                        stats_cache.set(host, {"error": str(result)})
                        await self._update_db_status(host, "offline")
                    elif result:
                        stats_cache.set(host, result)
                        await self._update_db_status(host, "online", result)

                await asyncio.sleep(self.poll_interval)
        finally:
            self._running = False
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
        logger.info("[SwitchMonitorScheduler] Stopped.")

    async def _poll_host(self, host: str) -> dict:
        return await asyncio.to_thread(switch_connector.fetch_switch_stats, host)


# Singleton
switch_monitor_scheduler = SwitchMonitorScheduler()
