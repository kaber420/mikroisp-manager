# app/utils/device_clients/adapters/mikrotik_wireless.py
"""
MikroTik Wireless adapter.
Reuses the existing MikroTik connection infrastructure for efficiency.
Supports both legacy 'wireless' and new 'wifi/wifiwave2' packages.
"""

import logging
from typing import List, Optional, Dict, Any

from routeros_api import RouterOsApiPool
from routeros_api.api import RouterOsApi

from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
# Reuse existing MikroTik utilities
from ..mikrotik import system as mikrotik_system
from ..mikrotik import connection as mikrotik_connection
from ..mikrotik.interfaces import MikrotikInterfaceManager
from ..mikrotik import parsers as mikrotik_parsers

logger = logging.getLogger(__name__)


class MikrotikWirelessAdapter(BaseDeviceAdapter):
    """
    Adapter for MikroTik wireless devices (RouterOS).
    
    Uses cached connection pools for efficiency - MikroTik API maintains
    persistent connections unlike Ubiquiti which needs HTTP auth each time.
    
    Can also accept an existing API connection to avoid creating new pools.
    """
    
    def __init__(
        self, 
        host: str, 
        username: str, 
        password: str, 
        port: int = 8729,
        api: RouterOsApi = None  # Optional: use existing API connection
    ):
        super().__init__(host, username, password, port)
        self._external_api = api  # If provided, we don't manage the connection
        self._own_pool = False  # Track if we created our own pool
        self._wireless_type = None  # Will be detected: 'wireless', 'wifi', 'wifiwave2', or None
    
    @property
    def vendor(self) -> str:
        return "mikrotik"
    
    def _get_api(self) -> RouterOsApi:
        """
        Get an API connection.
        Uses external API if provided, otherwise uses cached pool.
        """
        if self._external_api:
            return self._external_api
        
        # Use centralized connection manager (efficient - reuses connection)
        pool = mikrotik_connection.get_pool(self.host, self.username, self.password, self.port)
        self._own_pool = True
        return pool.get_api()
    
    def _detect_wireless_type(self, api: RouterOsApi) -> Optional[str]:
        """
        Detect which wireless package is installed on the device.
        Uses the centralized MikrotikInterfaceManager for detection.
        Returns: 'wireless', 'wifi', 'wifiwave2', or None if no wireless.
        """
        if self._wireless_type is not None:
            return self._wireless_type
        
        # Use the centralized interface manager for detection
        manager = MikrotikInterfaceManager(api)
        _, wtype = manager.get_wireless_interfaces()
        self._wireless_type = wtype
        
        if wtype:
            logger.debug(f"Detected wireless type '{wtype}' on {self.host}")
        else:
            logger.debug(f"No wireless interface detected on {self.host}")
        
        return self._wireless_type
    
    def _get_registration_table_path(self, api: RouterOsApi = None) -> Optional[str]:
        """Get the registration table path based on wireless type. Uses centralized manager."""
        manager = MikrotikInterfaceManager(api) if api else None
        if manager:
            return manager.get_registration_table_path(self._wireless_type)
        # Fallback for when no API is provided (should not happen in practice)
        paths = {
            "wireless": "/interface/wireless/registration-table",
            "wifi": "/interface/wifi/registration-table", 
            "wifiwave2": "/interface/wifiwave2/registration-table",
        }
        return paths.get(self._wireless_type)
    
    def _get_wireless_interface_path(self, api: RouterOsApi = None) -> Optional[str]:
        """Get the wireless interface path based on wireless type. Uses centralized manager."""
        manager = MikrotikInterfaceManager(api) if api else None
        if manager:
            return manager.get_wireless_interface_path(self._wireless_type)
        # Fallback for when no API is provided
        paths = {
            "wireless": "/interface/wireless",
            "wifi": "/interface/wifi",
            "wifiwave2": "/interface/wifiwave2",
        }
        return paths.get(self._wireless_type)

    def get_status(self) -> DeviceStatus:
        """Fetch live status from the MikroTik device."""
        try:
            api = self._get_api()
            
            # Use existing system utilities (same as RouterService does)
            system_data = mikrotik_system.get_system_resources(api)
            
            # Get system MAC address as fallback
            system_mac = None
            try:
                interfaces = api.get_resource("/interface").get()
                # Find first ethernet or bridge interface for MAC
                for iface in interfaces:
                    if iface.get("type") in ["ether", "bridge"]:
                        system_mac = iface.get("mac-address")
                        if system_mac:
                            break
            except Exception as e:
                logger.debug(f"Could not get system MAC: {e}")
            
            # Detect wireless type
            wireless_type = self._detect_wireless_type(api)
            
            # Get wireless interface info if available
            wireless_info = {}
            if wireless_type:
                wireless_path = self._get_wireless_interface_path(api)
                try:
                    wireless_interfaces = api.get_resource(wireless_path).get()
                    if wireless_interfaces:
                        # Use first interface for basic info (SSID, MAC, etc.)
                        wlan = wireless_interfaces[0]
                        interface_name = wlan.get("name") or wlan.get("default-name")
                        
                        # Field names differ between packages:
                        # - wireless (legacy ROS6): ssid, frequency, channel-width, mac-address
                        # - wifi/wifiwave2 (ROS7+): configuration.ssid, channel.width, mac-address
                        
                        # Try ROS7 wifi format first, then legacy
                        ssid = (wlan.get("configuration.ssid") or 
                                wlan.get("ssid") or 
                                wlan.get("name"))
                        
                        # Channel width: ROS7 uses channel.width
                        channel_width = (wlan.get("channel.width") or 
                                        wlan.get("channel-width"))
                        
                        # MAC address
                        mac = wlan.get("mac-address")
                        
                        # Band info - ROS7 uses channel.band
                        band = wlan.get("channel.band") or wlan.get("band")
                        
                        # Mode: ROS7 uses configuration.mode
                        mode = wlan.get("configuration.mode") or wlan.get("mode")
                        
                        # Get actual frequency from monitor (ROS7)
                        # Monitor returns channel like "5220/ax/eeCe" where 5220 is the frequency
                        frequency = None
                        tx_power = None
                        if wireless_type in ["wifi", "wifiwave2"] and interface_name:
                            try:
                                # Use call to get monitor data
                                monitor_result = api.get_resource(wireless_path).call(
                                    "monitor", {"numbers": interface_name, "once": ""}
                                )
                                if monitor_result:
                                    monitor_data = monitor_result[0] if isinstance(monitor_result, list) else monitor_result
                                    channel_info = monitor_data.get("channel", "")
                                    # Parse frequency from channel string (e.g., "5220/ax/eeCe")
                                    if channel_info and "/" in channel_info:
                                        freq_str = channel_info.split("/")[0]
                                        try:
                                            frequency = int(freq_str)
                                        except ValueError:
                                            pass
                                    tx_power = monitor_data.get("tx-power")
                                    logger.debug(f"Monitor data: channel={channel_info}, tx_power={tx_power}")
                            except Exception as e:
                                logger.debug(f"Could not get monitor data for {interface_name}: {e}")
                        
                        # Fallback to legacy frequency field
                        if not frequency:
                            frequency = self._parse_frequency(wlan.get("frequency"))
                        
                        wireless_info = {
                            "ssid": ssid,
                            "frequency": frequency,
                            "band": band,
                            "channel_width": channel_width,
                            "mac": mac or system_mac,
                            "mode": mode,
                            "noise_floor": mikrotik_parsers.parse_signal(wlan.get("noise-floor")),
                            "tx_power": tx_power,
                        }
                        logger.debug(f"Parsed wireless_info: {wireless_info}")
                        
                        # Get AGGREGATE throughput from ALL wireless interfaces
                        total_tx_throughput_kbps = 0.0
                        total_rx_throughput_kbps = 0.0
                        
                        for wlan_iface in wireless_interfaces:
                            iface_name = wlan_iface.get("name") or wlan_iface.get("default-name")
                            if iface_name:
                                try:
                                    traffic_result = api.get_resource("/interface").call(
                                        "monitor-traffic", {"interface": iface_name, "once": ""}
                                    )
                                    if traffic_result:
                                        traffic_data = traffic_result[0] if isinstance(traffic_result, list) else traffic_result
                                        tx_kbps = mikrotik_parsers.parse_throughput_bps(traffic_data.get("tx-bits-per-second")) or 0
                                        rx_kbps = mikrotik_parsers.parse_throughput_bps(traffic_data.get("rx-bits-per-second")) or 0
                                        total_tx_throughput_kbps += tx_kbps
                                        total_rx_throughput_kbps += rx_kbps
                                        logger.debug(f"Interface {iface_name}: tx={tx_kbps}kbps, rx={rx_kbps}kbps")
                                except Exception as e:
                                    logger.debug(f"Could not get interface traffic for {iface_name}: {e}")
                        
                        wireless_info["tx_throughput_kbps"] = total_tx_throughput_kbps if total_tx_throughput_kbps > 0 else None
                        wireless_info["rx_throughput_kbps"] = total_rx_throughput_kbps if total_rx_throughput_kbps > 0 else None
                        logger.debug(f"Total AP throughput: tx={total_tx_throughput_kbps}kbps, rx={total_rx_throughput_kbps}kbps")
                except Exception as e:
                    logger.warning(f"Could not get wireless interface info: {e}")

            
            # Get connected clients
            clients = self._get_clients_internal(api)
            
            # Calculate aggregate stats from WIRELESS INTERFACES (not clients)
            # This ensures total data persists even when clients disconnect.
            total_tx_bytes = 0
            total_rx_bytes = 0
            avg_noise_floor = None
            noise_samples = []
            
            # Sum tx-byte/rx-byte from PHYSICAL wireless interfaces only (wifi1, wifi2, wlan1, wlan2)
            # Virtual interfaces share stats with their parent, so we exclude them to avoid duplication.
            if wireless_type and wireless_interfaces:
                # First, identify physical interface names (those without a master)
                physical_iface_names = set()
                for wlan_iface in wireless_interfaces:
                    iface_name = wlan_iface.get("name") or wlan_iface.get("default-name")
                    # Check for master-interface - if present, this is a virtual interface
                    master = wlan_iface.get("master-interface") or wlan_iface.get("configuration.master")
                    if iface_name and not master:
                        # Physical interfaces are named wifi1, wifi2, wlan1, wlan2, etc.
                        if iface_name.startswith(("wifi", "wlan")) and iface_name[-1].isdigit():
                            physical_iface_names.add(iface_name)
                
                logger.debug(f"Physical wireless interfaces for stats: {physical_iface_names}")
                
                # Get stats for all interfaces at once
                try:
                    all_iface_stats = api.get_resource("/interface").call("print", {"stats": ""})
                    for stats in all_iface_stats:
                        iface_name = stats.get("name")
                        if iface_name in physical_iface_names:
                            tx_b = mikrotik_parsers.parse_int(stats.get("tx-byte"))
                            rx_b = mikrotik_parsers.parse_int(stats.get("rx-byte"))
                            logger.debug(f"Interface {iface_name} stats: tx={tx_b}, rx={rx_b}")
                            if tx_b:
                                total_tx_bytes += tx_b
                            if rx_b:
                                total_rx_bytes += rx_b
                except Exception as e:
                    logger.warning(f"Could not get interface stats: {e}")
                
                logger.debug(f"Total interface bytes: tx={total_tx_bytes}, rx={total_rx_bytes}")
            
            for client in clients:
                if client.noisefloor:
                    noise_samples.append(client.noisefloor)
            
            # Use average noise floor from clients if interface doesn't provide it
            if noise_samples:
                avg_noise_floor = sum(noise_samples) // len(noise_samples)
            
            noise_floor = wireless_info.get("noise_floor") or avg_noise_floor
            
            # Parse uptime from system data
            uptime_seconds = mikrotik_parsers.parse_uptime(system_data.get("uptime", "0s"))
            
            return DeviceStatus(
                host=self.host,
                vendor=self.vendor,
                role="access_point",
                hostname=system_data.get("name"),
                model=system_data.get("model") or system_data.get("board-name"),
                mac=wireless_info.get("mac"),
                firmware=system_data.get("version"),
                uptime=uptime_seconds,
                is_online=True,
                frequency=mikrotik_parsers.parse_frequency(wireless_info.get("frequency")),
                channel_width=mikrotik_parsers.parse_channel_width(wireless_info.get("channel_width")),
                essid=wireless_info.get("ssid"),
                noise_floor=noise_floor,
                client_count=len(clients),
                tx_bytes=total_tx_bytes if total_tx_bytes > 0 else None,
                rx_bytes=total_rx_bytes if total_rx_bytes > 0 else None,
                tx_throughput=int(wireless_info.get("tx_throughput_kbps") or 0) or None,
                rx_throughput=int(wireless_info.get("rx_throughput_kbps") or 0) or None,
                clients=clients,
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
    
    def _get_clients_internal(self, api: RouterOsApi) -> List[ConnectedClient]:
        """Get connected clients using provided API connection."""
        try:
            # Detect wireless type if not already done
            if self._wireless_type is None:
                self._detect_wireless_type(api)
            
            if not self._wireless_type:
                return []
            
            reg_path = self._get_registration_table_path(api)
            if not reg_path:
                return []
            
            # Get registration table with stats for throughput data
            # For ROS7 wifi, we need to use call with stats or proplist
            registrations = []
            try:
                # Try to get with stats (ROS7 wifi)
                registrations = api.get_resource(reg_path).call("print", {"stats": ""})
                logger.debug(f"Got registrations with stats: {len(registrations)} clients")
            except Exception as e:
                logger.debug(f"Stats call failed: {e}, using regular get")
                # Fallback to regular get
                registrations = api.get_resource(reg_path).get()
            
            clients = []
            
            for reg in registrations:
                signal = mikrotik_parsers.parse_signal(reg.get("signal-strength") or reg.get("signal"))
                tx_rate = mikrotik_parsers.parse_rate(reg.get("tx-rate"))
                rx_rate = mikrotik_parsers.parse_rate(reg.get("rx-rate"))
                tx_bytes, rx_bytes = mikrotik_parsers.parse_bytes(reg.get("bytes"))
                
                # Parse throughput from stats fields (in bits per second, convert to kbps)
                tx_throughput_kbps = mikrotik_parsers.parse_throughput_bps(reg.get("tx-bits-per-second"))
                rx_throughput_kbps = mikrotik_parsers.parse_throughput_bps(reg.get("rx-bits-per-second"))
                
                clients.append(ConnectedClient(
                    mac=reg.get("mac-address"),
                    hostname=reg.get("comment"),
                    ip_address=reg.get("last-ip"),
                    signal=signal,
                    tx_rate=tx_rate,
                    rx_rate=rx_rate,
                    ccq=mikrotik_parsers.parse_int(reg.get("tx-ccq") or reg.get("ccq")),
                    tx_bytes=tx_bytes,
                    rx_bytes=rx_bytes,
                    tx_throughput_kbps=int(tx_throughput_kbps) if tx_throughput_kbps else None,
                    rx_throughput_kbps=int(rx_throughput_kbps) if rx_throughput_kbps else None,
                    uptime=mikrotik_parsers.parse_uptime(reg.get("uptime", "0s")),
                    interface=reg.get("interface"),
                    extra={
                        "rx_signal": reg.get("signal-strength"),
                        "signal_ch0": reg.get("signal-strength-ch0"),
                        "signal_ch1": reg.get("signal-strength-ch1"),
                        "noise_floor": reg.get("noise-floor"),
                        "p_throughput": reg.get("p-throughput"),
                        "distance": reg.get("distance"),
                        "band": reg.get("band"),
                        "auth_type": reg.get("auth-type"),
                    }
                ))
            
            return clients
            
        except Exception as e:
            logger.error(f"Error getting clients from {self.host}: {e}")
            return []
    
    def get_connected_clients(self) -> List[ConnectedClient]:
        """Get the list of connected clients from registration table."""
        api = self._get_api()
        return self._get_clients_internal(api)
    
    def test_connection(self) -> bool:
        """Test if the device is reachable."""
        try:
            api = self._get_api()
            resources = api.get_resource("/system/resource").get()
            return len(resources) > 0
        except Exception as e:
            logger.error(f"Connection test failed for {self.host}: {e}")
            # Invalidate cache on failure
            mikrotik_connection.remove_pool(self.host, self.port, username=self.username)
            return False
    
    def disconnect(self):
        """
        Cierra el pool de conexiones.
        """
        # Reset wireless type detection for next call
        self._wireless_type = None
        
        # If we were given an external API, we don't manage it
        if self._external_api:
            self._external_api = None
            return
        
        # Close and remove pool from cache
        if self._own_pool:
            mikrotik_connection.remove_pool(self.host, self.port, username=self.username)
            self._own_pool = False
    
    # --- Helper methods ---
    # NOTE: Parsing logic has been centralized in app/utils/device_clients/mikrotik/parsers.py
    # Use mikrotik_parsers.parse_* functions instead of private methods.


