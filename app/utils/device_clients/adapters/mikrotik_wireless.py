# app/utils/device_clients/adapters/mikrotik_wireless.py
"""
MikroTik Wireless adapter.
Reuses the existing MikroTik connection infrastructure for efficiency.
Supports both legacy 'wireless' and new 'wifi/wifiwave2' packages.
"""

import logging
from typing import List, Optional, Dict, Any

from routeros_api.api import RouterOsApi

from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
# Reuse existing MikroTik utilities
from ..mikrotik import system as mikrotik_system
from ..mikrotik import connection as mikrotik_connection
from ..mikrotik import parsers as mikrotik_parsers
# NEW: Import the shared wireless module
from ..mikrotik import wireless as mikrotik_wireless_lib

logger = logging.getLogger(__name__)


from .mikrotik_router import MikrotikRouterAdapter

class MikrotikWirelessAdapter(MikrotikRouterAdapter):
    """
    Adapter for MikroTik wireless devices (AP).
    Inherits all Router capabilities (IP, Firewall, Queues, etc.) 
    and adds Wireless-specific monitoring functionality.
    """
    
    def __init__(
        self, 
        host: str, 
        username: str, 
        password: str, 
        port: int = 8729,
        api: RouterOsApi = None
    ):
        # Initialize the Router adapter (which handles connection pooling)
        super().__init__(host, username, password, port, api)
    
    @property
    def vendor(self) -> str:
        return "mikrotik"
    
    # _get_api is already implemented in MikrotikRouterAdapter
    
    def get_status(self) -> DeviceStatus:
        """Fetch live status from the MikroTik device."""
        try:
            api = self._get_api()
            
            # 1. System Resources (Shared Module)
            system_data = mikrotik_system.get_system_resources(api)
            
            # 2. Wireless Info (Shared Module)
            # Get detailed list of interfaces
            wireless_interfaces = mikrotik_wireless_lib.get_wireless_interfaces_detailed(api)
            
            # Detect main properties from the first found wireless interface
            wireless_info = {}
            wireless_type = None
            
            if wireless_interfaces:
                # Use the first interface as the "Main" one for AP summary
                main_iface = wireless_interfaces[0]
                wireless_type = main_iface.get("type")
                
                wireless_info = {
                    "ssid": (
                        main_iface.get("original_record", {}).get("configuration.ssid") or 
                        main_iface.get("original_record", {}).get("ssid") or 
                        main_iface["name"]
                    ),
                    "frequency": mikrotik_parsers.parse_frequency(main_iface.get("frequency")),
                    "band": main_iface.get("band"),
                    "channel_width": mikrotik_parsers.parse_channel_width(main_iface.get("width")),
                    "mac": main_iface.get("original_record", {}).get("mac-address"),
                    "tx_power": main_iface.get("tx_power")
                }
            else:
                 # Check if we at least detected a type even without active interfaces
                 wireless_type = mikrotik_wireless_lib.get_wireless_type(api)

            # 3. Aggregate Stats (Shared Module)
            stats = mikrotik_wireless_lib.get_aggregate_interface_stats(api)
            
            # 4. Connected Clients (Shared Module)
            clients_list = mikrotik_wireless_lib.get_connected_clients(api)
            
            # Convert dicts to ConnectedClient objects
            connected_clients = []
            noise_samples = []
            
            for c in clients_list:
                # Extract extra data for client object
                extra_data = c.get("extra", {})
                
                # Collect noise floor samples
                nf = c.get("noise_floor")
                if nf: 
                    # Try to parse if it's a string, though wireless_lib might pass raw
                    parsed_nf = mikrotik_parsers.parse_int(nf) or mikrotik_parsers.parse_signal(str(nf))
                    if parsed_nf:
                        noise_samples.append(parsed_nf)

                connected_clients.append(ConnectedClient(
                    mac=c["mac"],
                    hostname=c["hostname"],
                    ip_address=c["ip_address"],
                    signal=c["signal"],
                    tx_rate=c["tx_rate"],
                    rx_rate=c["rx_rate"],
                    ccq=c["ccq"],
                    tx_bytes=c["tx_bytes"],
                    rx_bytes=c["rx_bytes"],
                    tx_throughput_kbps=c["tx_throughput_kbps"],
                    rx_throughput_kbps=c["rx_throughput_kbps"],
                    uptime=c["uptime"],
                    interface=c["interface"],
                    extra=extra_data
                ))
            
            # Calculate average noise floor if not available from interface
            avg_noise_floor = None
            if noise_samples:
                avg_noise_floor = sum(noise_samples) // len(noise_samples)
            
            noise_floor_val = None
            # Some interfaces provide noise floor directly, but our detailed list doesn't extract it by default
            # We can use the average from clients as a good fallback
            noise_floor_val = avg_noise_floor

            # 5. System MAC fallback
            system_mac = wireless_info.get("mac")
            if not system_mac:
                # Fallback to finding an ethernet mac
                try:
                    all_ethers = mikrotik_system.get_interfaces(api) # Reusing existing system module function
                    for iface in all_ethers:
                         if iface.get("mac-address"):
                             system_mac = iface.get("mac-address")
                             break
                except Exception:
                    pass

            uptime_seconds = mikrotik_parsers.parse_uptime(system_data.get("uptime", "0s"))
            
            return DeviceStatus(
                host=self.host,
                vendor=self.vendor,
                role="access_point",
                hostname=system_data.get("name"),
                model=system_data.get("model") or system_data.get("board-name"),
                mac=system_mac,
                firmware=system_data.get("version"),
                uptime=uptime_seconds,
                is_online=True,
                frequency=wireless_info.get("frequency"),
                channel_width=wireless_info.get("channel_width"),
                essid=wireless_info.get("ssid"),
                noise_floor=noise_floor_val,
                client_count=len(connected_clients),
                tx_bytes=stats["tx_bytes"],
                rx_bytes=stats["rx_bytes"],
                tx_throughput=stats["tx_throughput"] or None,
                rx_throughput=stats["rx_throughput"] or None,
                clients=connected_clients,
                extra={
                    "cpu_load": system_data.get("cpu-load"),
                    "free_memory": system_data.get("free-memory"),
                    "total_memory": system_data.get("total-memory"),
                    "platform": system_data.get("platform"),
                    "band": wireless_info.get("band"),
                    "wireless_type": wireless_type,
                    "has_wireless": wireless_type is not None,
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting status from {self.host}: {e}")
            # On error, invalidate the cached pool so next request creates fresh connection
            mikrotik_connection.remove_pool(self.host, self.port, username=self.username)
            return DeviceStatus(
                host=self.host,
                vendor=self.vendor,
                role="access_point",
                is_online=False,
                last_error=str(e)
            )
    
    def get_connected_clients(self) -> List[ConnectedClient]:
        """Get the list of connected clients from registration table."""
        api = self._get_api()
        
        # Use shared module
        clients_data = mikrotik_wireless_lib.get_connected_clients(api)
        
        # Convert to objects
        return [
            ConnectedClient(
                mac=c["mac"],
                hostname=c["hostname"],
                ip_address=c["ip_address"],
                signal=c["signal"],
                tx_rate=c["tx_rate"],
                rx_rate=c["rx_rate"],
                ccq=c["ccq"],
                tx_bytes=c["tx_bytes"],
                rx_bytes=c["rx_bytes"],
                tx_throughput_kbps=c["tx_throughput_kbps"],
                rx_throughput_kbps=c["rx_throughput_kbps"],
                uptime=c["uptime"],
                interface=c["interface"],
                extra=c.get("extra", {})
            )
            for c in clients_data
        ]
    
    def test_connection(self) -> bool:
        """Test if the device is reachable."""
        try:
            api = self._get_api()
            # Reuse system module for lightness
            resources = mikrotik_system.get_system_resources(api)
            return True if resources else False
        except Exception as e:
            logger.error(f"Connection test failed for {self.host}: {e}")
            mikrotik_connection.remove_pool(self.host, self.port, username=self.username)
            return False
    

