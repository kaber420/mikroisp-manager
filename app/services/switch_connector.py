import asyncio
import logging
from typing import Dict
from datetime import datetime

from .switch_service import SwitchService
from ..db import switches_db

logger = logging.getLogger(__name__)


class SwitchConnector:
    """
    Abstraction layer for Switch connection management.
    Uses SwitchService directly for fetching stats.
    """
    
    def __init__(self):
        self._credentials: Dict[str, dict] = {}  # host -> switch_data
        logger.info("[SwitchConnector] Initialized")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Subscribe to a switch by storing its credentials.
        Connection is made on-demand during fetch.
        """
        # Get full switch data from DB for SwitchService
        switch_data = await asyncio.to_thread(switches_db.get_switch_by_host, host)
        if switch_data:
            self._credentials[host] = switch_data
            logger.info(f"[SwitchConnector] Subscribed to {host}")
        else:
            logger.error(f"[SwitchConnector] Switch {host} not found in DB")
            raise ValueError(f"Switch {host} not found")
    
    async def unsubscribe(self, host: str) -> None:
        """Unsubscribe from a switch."""
        # Nothing to release since we connect on-demand
        logger.debug(f"[SwitchConnector] Unsubscribed from {host}")
            
    def cleanup_credentials(self, host: str) -> None:
        """Clean up stored credentials for a host."""
        if host in self._credentials:
            del self._credentials[host]
    
    def fetch_switch_stats(self, host: str) -> dict:
        """
        Fetch monitoring statistics from a switch using SwitchService.
        """
        if host not in self._credentials:
            raise ValueError(f"Switch {host} is not subscribed")
        
        switch_data = self._credentials[host]
        service = None
        
        try:
            service = SwitchService(host, switch_data)
            resources = service.get_system_resources()
            
            return {
                "cpu_load": resources.get("cpu-load"),
                "free_memory": resources.get("free-memory"),
                "total_memory": resources.get("total-memory"),
                "uptime": resources.get("uptime"),
                "version": resources.get("version"),
                "board_name": resources.get("board-name"),
                "name": resources.get("name"),
                "hostname": resources.get("name"),
                "total_disk": resources.get("total-hdd-space", resources.get("total-disk-space")),
                "free_disk": resources.get("free-hdd-space", resources.get("free-disk-space")),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[SwitchConnector] Error fetching stats from {host}: {e}")
            return {"error": str(e)}
        finally:
            if service:
                try:
                    service.disconnect()
                except:
                    pass


# Singleton instance
switch_connector = SwitchConnector()
