import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

from ..core.constants import CredentialKeys
from ..utils.device_clients.mikrotik.channels import readonly_channels

logger = logging.getLogger(__name__)


class RouterConnector:
    """
    Abstraction layer for router connection management.
    
    Responsibilities:
    - Manage router credentials
    - Handle connection lifecycle (subscribe/unsubscribe)
    - Provide high-level data fetching methods
    - Encapsulate retry logic and error handling
    - Hide ReadOnlyChannelManager implementation details
    """
    
    def __init__(self):
        self._credentials: Dict[str, dict] = {}  # host -> creds
        logger.info("[RouterConnector] Initialized")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Subscribe to a router by establishing a persistent connection.
        Stores credentials for later use in polling.
        
        Args:
            host: Router hostname/IP
            creds: Dictionary with keys: username, password, port (optional)
        """
        # Store credentials for this host
        self._credentials[host] = creds
        
        # Establish physical connection via channel manager
        # (offload blocking I/O to thread pool)
        try:
            await asyncio.to_thread(
                readonly_channels.acquire,
                host,
                creds[CredentialKeys.USERNAME],
                creds[CredentialKeys.PASSWORD],
                creds.get(CredentialKeys.PORT, 8729)
            )
            logger.info(f"[RouterConnector] Subscribed to {host}")
        except Exception as e:
            logger.error(f"[RouterConnector] Failed to subscribe to {host}: {e}")
            # Remove credentials on failure
            if host in self._credentials:
                del self._credentials[host]
            raise
    
    async def unsubscribe(self, host: str) -> None:
        """
        Unsubscribe from a router, releasing the connection.
        NOTE: Credentials are NOT deleted here. The MonitorScheduler will
        call cleanup_credentials() when ref_count reaches 0.
        
        Args:
            host: Router hostname/IP
        """
        if host not in self._credentials:
            logger.warning(f"[RouterConnector] Attempted to unsubscribe from unknown host: {host}")
            return
        
        # Get port before potentially deleting credentials
        creds = self._credentials[host]
        port = creds.get(CredentialKeys.PORT, 8729)
        
        # Release physical connection (offload blocking I/O)
        try:
            await asyncio.to_thread(readonly_channels.release, host, port)
            logger.debug(f"[RouterConnector] Released connection for {host}")
        except Exception as e:
            logger.error(f"[RouterConnector] Error releasing connection for {host}: {e}")
        
        # DO NOT delete credentials here - let scheduler coordinate cleanup
        # when ref_count reaches 0
    
    def cleanup_credentials(self, host: str) -> None:
        """
        Clean up stored credentials for a host.
        Called by MonitorScheduler when ref_count reaches 0.
        
        Args:
            host: Router hostname/IP
        """
        if host in self._credentials:
            del self._credentials[host]
            logger.info(f"[RouterConnector] Cleaned up credentials for {host}")
    
    def fetch_router_stats(self, host: str) -> dict:
        """
        Fetch monitoring statistics from a router.
        This is a synchronous method (runs in thread pool from scheduler).
        
        Args:
            host: Router hostname/IP
            
        Returns:
            Dictionary with router statistics or error information
            
        Raises:
            Exception: If router is not subscribed or fetch fails
        """
        if host not in self._credentials:
            raise ValueError(f"Router {host} is not subscribed")
        
        creds = self._credentials[host]
        
        try:
            # Acquire API connection
            api = readonly_channels.acquire(
                host,
                creds[CredentialKeys.USERNAME],
                creds[CredentialKeys.PASSWORD],
                creds.get(CredentialKeys.PORT, 8729)
            )
            
            try:
                # Execute /system/resource command
                resource_list = api.get_resource("/system/resource").get()
                if not resource_list:
                    return {"error": "No data from /system/resource"}
                
                r = resource_list[0]
                
                # Execute /system/identity command to get hostname
                identity_list = []
                try:
                    identity_list = api.get_resource("/system/identity").get()
                except Exception:
                    pass

                hostname = identity_list[0].get("name") if identity_list else None

                # Execute /system/health command (optional, not all routers support it)
                health_list = []
                try:
                    health_list = api.get_resource("/system/health").get()
                except Exception:
                    pass  # Some routers don't have /system/health
                
                # Parse health data (handles both MikroTik formats)
                # Format A (Flat): [{'voltage': '24.5', 'temperature': '30'}]
                # Format B (Modular): [{'name': 'voltage', 'value': '24'}, ...]
                voltage = None
                temperature = None
                cpu_temperature = None
                
                for sensor in health_list:
                    # Format B (Modular with name/value pairs)
                    if "name" in sensor and "value" in sensor:
                        name = sensor["name"]
                        value = sensor["value"]
                        if name == "voltage":
                            voltage = value
                        elif name == "temperature":
                            temperature = value
                        elif name in ["cpu-temperature", "cpu-temp"]:
                            cpu_temperature = value
                    # Format A (Flat dictionary)
                    else:
                        if "voltage" in sensor:
                            voltage = sensor["voltage"]
                        if "temperature" in sensor:
                            temperature = sensor["temperature"]
                        if "cpu-temperature" in sensor:
                            cpu_temperature = sensor["cpu-temperature"]
                        if "cpu-temp" in sensor:
                            cpu_temperature = sensor["cpu-temp"]
                
                # Build response
                # Note: We provide both underscores and hyphens for compatibility with different consumers (DB vs Frontend)
                return {
                    "cpu_load": r.get("cpu-load"),
                    "free_memory": r.get("free-memory"),
                    "total_memory": r.get("total-memory"),
                    "uptime": r.get("uptime"),
                    "version": r.get("version"),
                    "board_name": r.get("board-name"),
                    "board-name": r.get("board-name"), # Computed for DB compatibility
                    "name": hostname, # Computed for DB compatibility (hostname)
                    "hostname": hostname, # Alias
                    "total_disk": r.get("total-hdd-space", r.get("total-disk-space")),
                    "free_disk": r.get("free-hdd-space", r.get("free-disk-space")),
                    "voltage": voltage,
                    "temperature": temperature,
                    "cpu_temperature": cpu_temperature,
                    "timestamp": datetime.now().isoformat()
                }
            
            finally:
                # Always release the API connection
                readonly_channels.release(host, creds.get(CredentialKeys.PORT, 8729))
        
        except Exception as e:
            logger.error(f"[RouterConnector] Error fetching stats from {host}: {e}")
            raise


# Singleton instance
router_connector = RouterConnector()
