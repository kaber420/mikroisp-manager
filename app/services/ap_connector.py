# app/services/ap_connector.py
"""
APConnector: Gestiona conexiones a APs multi-vendor.
Análogo a RouterConnector pero usando el patrón de adaptadores.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

from ..core.constants import CredentialKeys, DeviceVendor
from ..utils.device_clients.adapter_factory import get_device_adapter
from ..utils.device_clients.adapters.base import BaseDeviceAdapter, DeviceStatus

logger = logging.getLogger(__name__)


class APConnector:
    """
    Abstraction layer for AP connection management.
    
    Responsibilities:
    - Manage AP credentials and adapters
    - Handle connection lifecycle (subscribe/unsubscribe)
    - Provide high-level data fetching methods
    - Support multi-vendor (Ubiquiti, MikroTik)
    """
    
    def __init__(self):
        self._adapters: Dict[str, BaseDeviceAdapter] = {}  # host -> adapter
        self._credentials: Dict[str, dict] = {}  # host -> creds
        logger.info("[APConnector] Initialized")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Subscribe to an AP by creating a persistent adapter.
        
        Args:
            host: AP hostname/IP
            creds: Dictionary with keys: username, password, vendor, port
        """
        # Store credentials
        self._credentials[host] = creds
        
        # Create adapter (offload to thread pool as some adapters may block)
        try:
            adapter = await asyncio.to_thread(
                get_device_adapter,
                host=host,
                username=creds[CredentialKeys.USERNAME],
                password=creds[CredentialKeys.PASSWORD],
                vendor=creds.get("vendor", DeviceVendor.MIKROTIK),
                port=creds.get(CredentialKeys.PORT, 8729)
            )
            self._adapters[host] = adapter
            logger.info(f"[APConnector] Subscribed to {host} ({creds.get('vendor', DeviceVendor.MIKROTIK)})")
        except Exception as e:
            logger.error(f"[APConnector] Failed to subscribe to {host}: {e}")
            if host in self._credentials:
                del self._credentials[host]
            raise
    
    async def unsubscribe(self, host: str) -> None:
        """
        Unsubscribe from an AP.
        NOTE: Does NOT clean up immediately - MonitorScheduler handles cleanup.
        
        Args:
            host: AP hostname/IP
        """
        if host not in self._credentials:
            logger.warning(f"[APConnector] Attempted to unsubscribe from unknown host: {host}")
            return
        
        logger.debug(f"[APConnector] Marked {host} for potential cleanup")
    
    def cleanup(self, host: str) -> None:
        """
        Clean up adapter and credentials for a host.
        Called by APMonitorScheduler when ref_count reaches 0.
        
        Args:
            host: AP hostname/IP
        """
        if host in self._adapters:
            try:
                self._adapters[host].disconnect()
            except Exception as e:
                logger.error(f"[APConnector] Error disconnecting {host}: {e}")
            del self._adapters[host]
        
        if host in self._credentials:
            del self._credentials[host]
        
        logger.info(f"[APConnector] Cleaned up {host}")
    
    def fetch_ap_stats(self, host: str) -> dict:
        """
        Fetch monitoring statistics from an AP.
        This is a synchronous method (runs in thread pool from scheduler).
        
        Args:
            host: AP hostname/IP
            
        Returns:
            Dictionary with AP statistics
            
        Raises:
            Exception: If AP is not subscribed or fetch fails
        """
        if host not in self._adapters:
            raise ValueError(f"AP {host} is not subscribed")
        
        adapter = self._adapters[host]
        
        try:
            status: DeviceStatus = adapter.get_status()
            
            if not status.is_online:
                return {"error": status.last_error or "AP offline"}
            
            # Convert clients to serializable format
            clients_list = []
            for client in status.clients:
                clients_list.append({
                    "mac": client.mac,
                    "hostname": client.hostname,
                    "ip_address": client.ip_address,
                    "signal": client.signal,
                    "signal_chain0": client.signal_chain0,
                    "signal_chain1": client.signal_chain1,
                    "noisefloor": client.noisefloor,
                    "tx_rate": client.tx_rate,
                    "rx_rate": client.rx_rate,
                    "ccq": client.ccq,
                    "tx_bytes": client.tx_bytes,
                    "rx_bytes": client.rx_bytes,
                    "tx_throughput_kbps": client.tx_throughput_kbps,
                    "rx_throughput_kbps": client.rx_throughput_kbps,
                    "extra": client.extra,
                })
            
            # Format uptime
            uptime_str = "--"
            if status.uptime:
                days = status.uptime // 86400
                hours = (status.uptime % 86400) // 3600
                minutes = (status.uptime % 3600) // 60
                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    uptime_str = f"{hours}h {minutes}m"
                else:
                    uptime_str = f"{minutes}m"
            
            # Build response (compatible with WebSocket format)
            return {
                "host": host,
                "hostname": status.hostname,
                "model": status.model,
                "mac": status.mac,
                "firmware": status.firmware,
                "vendor": status.vendor,
                "client_count": status.client_count or len(clients_list),
                "noise_floor": status.noise_floor,
                "chanbw": status.channel_width,
                "frequency": status.frequency,
                "essid": status.essid,
                "total_tx_bytes": status.tx_bytes,
                "total_rx_bytes": status.rx_bytes,
                "total_throughput_tx": status.tx_throughput,
                "total_throughput_rx": status.rx_throughput,
                "airtime_total_usage": status.airtime_usage,
                "airtime_tx_usage": status.extra.get("airtime_tx") if status.extra else None,
                "airtime_rx_usage": status.extra.get("airtime_rx") if status.extra else None,
                "clients": clients_list,
                "extra": {
                    "cpu_load": status.extra.get("cpu_load", 0) if status.extra else 0,
                    "free_memory": status.extra.get("free_memory") if status.extra else None,
                    "total_memory": status.extra.get("total_memory") if status.extra else None,
                    "uptime": uptime_str,
                    "platform": status.extra.get("platform") if status.extra else None,
                    "wireless_type": status.extra.get("wireless_type") if status.extra else None,
                },
                "timestamp": datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"[APConnector] Error fetching stats from {host}: {e}")
            raise


# Singleton instance
ap_connector = APConnector()
