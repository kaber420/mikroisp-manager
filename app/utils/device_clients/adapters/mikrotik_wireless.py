# app/utils/device_clients/adapters/mikrotik_wireless.py
"""
MikroTik Wireless adapter.
Reuses the existing MikroTik connection infrastructure for efficiency.
Supports both legacy 'wireless' and new 'wifi/wifiwave2' packages.
"""

import ssl
import logging
from typing import List, Optional, Dict, Any

from routeros_api import RouterOsApiPool
from routeros_api.api import RouterOsApi

from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
# Reuse existing MikroTik utilities
from ..mikrotik import system as mikrotik_system

logger = logging.getLogger(__name__)

# Connection cache for MikroTik devices (similar to how routers work)
# Key: (host, port, username), Value: RouterOsApiPool
_mikrotik_pool_cache: Dict[tuple, RouterOsApiPool] = {}


def _get_cached_pool(host: str, username: str, password: str, port: int) -> RouterOsApiPool:
    """
    Get or create a cached connection pool for a MikroTik device.
    This prevents creating new SSL connections on every request.
    """
    cache_key = (host, port, username)
    
    if cache_key not in _mikrotik_pool_cache:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        _mikrotik_pool_cache[cache_key] = RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=port,
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True,
        )
        logger.debug(f"Created new MikroTik pool for {host}:{port}")
    
    return _mikrotik_pool_cache[cache_key]


def remove_cached_pool(host: str, port: int = 8729, username: str = None):
    """Remove a cached pool (e.g., when credentials change)."""
    keys_to_remove = [
        key for key in _mikrotik_pool_cache 
        if key[0] == host and (port is None or key[1] == port)
    ]
    for key in keys_to_remove:
        try:
            _mikrotik_pool_cache[key].disconnect()
        except Exception:
            pass
        del _mikrotik_pool_cache[key]


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
        
        # Use cached pool (efficient - reuses connection)
        pool = _get_cached_pool(self.host, self.username, self.password, self.port)
        self._own_pool = True
        return pool.get_api()
    
    def _detect_wireless_type(self, api: RouterOsApi) -> Optional[str]:
        """
        Detect which wireless package is installed on the device.
        Returns: 'wireless', 'wifi', 'wifiwave2', or None if no wireless.
        """
        if self._wireless_type is not None:
            return self._wireless_type
            
        # Try different wireless paths in order of preference
        wireless_paths = [
            ("/interface/wireless", "wireless"),
            ("/interface/wifi", "wifi"),
            ("/interface/wifiwave2", "wifiwave2"),
        ]
        
        for path, wtype in wireless_paths:
            try:
                result = api.get_resource(path).get()
                if result:  # Has at least one interface of this type
                    self._wireless_type = wtype
                    logger.debug(f"Detected wireless type '{wtype}' on {self.host}")
                    return wtype
            except Exception:
                # This path doesn't exist or isn't accessible
                continue
        
        logger.debug(f"No wireless interface detected on {self.host}")
        self._wireless_type = None
        return None
    
    def _get_registration_table_path(self) -> Optional[str]:
        """Get the registration table path based on wireless type."""
        paths = {
            "wireless": "/interface/wireless/registration-table",
            "wifi": "/interface/wifi/registration-table", 
            "wifiwave2": "/interface/wifiwave2/registration-table",
        }
        return paths.get(self._wireless_type)
    
    def _get_wireless_interface_path(self) -> Optional[str]:
        """Get the wireless interface path based on wireless type."""
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
                wireless_path = self._get_wireless_interface_path()
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
                            "noise_floor": self._parse_signal(wlan.get("noise-floor")),
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
                                        tx_kbps = self._parse_throughput_bps(traffic_data.get("tx-bits-per-second")) or 0
                                        rx_kbps = self._parse_throughput_bps(traffic_data.get("rx-bits-per-second")) or 0
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
            
            # Calculate aggregate stats from clients
            total_tx_bytes = 0
            total_rx_bytes = 0
            avg_noise_floor = None
            noise_samples = []
            
            for client in clients:
                if client.tx_bytes:
                    total_tx_bytes += client.tx_bytes
                if client.rx_bytes:
                    total_rx_bytes += client.rx_bytes
                if client.noisefloor:
                    noise_samples.append(client.noisefloor)
            
            # Use average noise floor from clients if interface doesn't provide it
            if noise_samples:
                avg_noise_floor = sum(noise_samples) // len(noise_samples)
            
            noise_floor = wireless_info.get("noise_floor") or avg_noise_floor
            
            # Parse uptime from system data
            uptime_seconds = self._parse_uptime(system_data.get("uptime", "0s"))
            
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
                frequency=self._parse_frequency(wireless_info.get("frequency")),
                channel_width=self._parse_channel_width(wireless_info.get("channel_width")),
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
            remove_cached_pool(self.host, self.port)
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
            
            reg_path = self._get_registration_table_path()
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
                signal = self._parse_signal(reg.get("signal-strength") or reg.get("signal"))
                tx_rate = self._parse_rate(reg.get("tx-rate"))
                rx_rate = self._parse_rate(reg.get("rx-rate"))
                tx_bytes, rx_bytes = self._parse_bytes(reg.get("bytes"))
                
                # Parse throughput from stats fields (in bits per second, convert to kbps)
                tx_throughput_kbps = self._parse_throughput_bps(reg.get("tx-bits-per-second"))
                rx_throughput_kbps = self._parse_throughput_bps(reg.get("rx-bits-per-second"))
                
                clients.append(ConnectedClient(
                    mac=reg.get("mac-address"),
                    hostname=reg.get("comment"),
                    ip_address=reg.get("last-ip"),
                    signal=signal,
                    tx_rate=tx_rate,
                    rx_rate=rx_rate,
                    ccq=self._parse_int(reg.get("tx-ccq") or reg.get("ccq")),
                    tx_bytes=tx_bytes,
                    rx_bytes=rx_bytes,
                    tx_throughput_kbps=int(tx_throughput_kbps) if tx_throughput_kbps else None,
                    rx_throughput_kbps=int(rx_throughput_kbps) if rx_throughput_kbps else None,
                    uptime=self._parse_uptime(reg.get("uptime", "0s")),
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
            remove_cached_pool(self.host, self.port)
            return False
    
    def disconnect(self):
        """
        Cleanup method.
        
        For MikroTik, we DON'T close the cached pool on disconnect()
        since we want to reuse it for subsequent requests.
        Only external API connections or on error do we cleanup.
        """
        # Reset wireless type detection for next call
        self._wireless_type = None
        
        # If we were given an external API, we don't manage it
        if self._external_api:
            self._external_api = None
            return
        
        # For cached pools, we keep them alive for reuse
        # They will be cleaned up on error or when explicitly removed
        pass
    
    # --- Helper methods ---
    
    def _parse_uptime(self, uptime_str: str) -> int:
        """Parse RouterOS uptime string to seconds."""
        if not uptime_str:
            return 0
        
        seconds = 0
        import re
        
        weeks = re.search(r"(\d+)w", uptime_str)
        days = re.search(r"(\d+)d", uptime_str)
        hours = re.search(r"(\d+)h", uptime_str)
        minutes = re.search(r"(\d+)m", uptime_str)
        secs = re.search(r"(\d+)s", uptime_str)
        
        if weeks:
            seconds += int(weeks.group(1)) * 7 * 24 * 3600
        if days:
            seconds += int(days.group(1)) * 24 * 3600
        if hours:
            seconds += int(hours.group(1)) * 3600
        if minutes:
            seconds += int(minutes.group(1)) * 60
        if secs:
            seconds += int(secs.group(1))
        
        return seconds
    
    def _parse_frequency(self, freq_str: Optional[str]) -> Optional[int]:
        """Parse frequency string to MHz."""
        if not freq_str:
            return None
        try:
            import re
            match = re.search(r"(\d+)", str(freq_str))
            return int(match.group(1)) if match else None
        except (ValueError, AttributeError):
            return None
    
    def _parse_channel_width(self, width_str: Optional[str]) -> Optional[int]:
        """Parse channel width string to MHz."""
        if not width_str:
            return None
        try:
            import re
            match = re.search(r"(\d+)", str(width_str))
            return int(match.group(1)) if match else None
        except (ValueError, AttributeError):
            return None
    
    def _parse_signal(self, signal_str: Optional[str]) -> Optional[int]:
        """Parse signal strength string to dBm."""
        if not signal_str:
            return None
        try:
            import re
            match = re.search(r"(-?\d+)", str(signal_str))
            return int(match.group(1)) if match else None
        except (ValueError, AttributeError):
            return None
    
    def _parse_rate(self, rate_str: Optional[str]) -> Optional[int]:
        """Parse rate string to Mbps."""
        if not rate_str:
            return None
        try:
            import re
            match = re.search(r"(\d+)", str(rate_str))
            return int(match.group(1)) if match else None
        except (ValueError, AttributeError):
            return None
    
    def _parse_bytes(self, bytes_str: Optional[str]) -> tuple:
        """Parse bytes string which may be 'rx,tx' format."""
        if not bytes_str:
            return None, None
        try:
            if "," in str(bytes_str):
                parts = str(bytes_str).split(",")
                rx = self._parse_int(parts[0]) if len(parts) > 0 else None
                tx = self._parse_int(parts[1]) if len(parts) > 1 else None
                return tx, rx
            return None, None
        except Exception:
            return None, None
    
    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Safely parse an integer from string."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_throughput_bps(self, throughput_str: Optional[str]) -> Optional[float]:
        """
        Parse throughput string to kbps.
        Handles both:
        - Raw bps numbers: '1032104' -> 1032.104 kbps
        - Formatted strings: '2.7Mbps', '89.1kbps', '0bps'
        Returns throughput in kbps (kilobits per second).
        """
        if not throughput_str:
            return None
        try:
            import re
            throughput_str = str(throughput_str).strip()
            
            # First try: if it's a plain number, treat as bps
            if throughput_str.isdigit() or (throughput_str.replace('.', '', 1).isdigit()):
                value_bps = float(throughput_str)
                return value_bps / 1000.0  # Convert bps to kbps
            
            # Second try: Pattern matches numbers (with optional decimals) and unit
            match = re.match(r"([\d.]+)\s*(Gbps|Mbps|kbps|bps)", throughput_str, re.IGNORECASE)
            if not match:
                return None
            
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to kbps
            if unit == "gbps":
                return value * 1_000_000
            elif unit == "mbps":
                return value * 1_000
            elif unit == "kbps":
                return value
            elif unit == "bps":
                return value / 1_000
            return None
        except (ValueError, AttributeError):
            return None

