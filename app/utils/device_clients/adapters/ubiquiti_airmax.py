# app/utils/device_clients/adapters/ubiquiti_airmax.py
"""
Ubiquiti AirMAX adapter.
Uses HTTP API to communicate with AirOS devices.
"""

import requests
import urllib3
from typing import List, Optional

from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
from ....core.constants import DeviceVendor, DeviceRole

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UbiquitiAirmaxAdapter(BaseDeviceAdapter):
    """
    Adapter for Ubiquiti AirMAX devices (AirOS).
    Communicates via HTTP/HTTPS API.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 443, use_https: bool = True):
        super().__init__(host, username, password, port)
        self.use_https = use_https
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}:{port}"
        self.session = requests.Session()
        self.session.verify = False
        self._is_authenticated = False
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 UManager/1.0",
            "Connection": "keep-alive",
        })
    
    @property
    def vendor(self) -> str:
        return DeviceVendor.UBIQUITI
    
    def _authenticate(self) -> bool:
        """Authenticate with the AirOS device."""
        self.session.cookies.clear()
        self._is_authenticated = False
        
        auth_url = f"{self.base_url}/api/auth"
        payload = {"username": self.username, "password": self.password}
        
        try:
            response = self.session.post(auth_url, data=payload, timeout=15)
            response.raise_for_status()
            
            csrf_token = response.headers.get("X-CSRF-ID")
            if csrf_token:
                self.session.headers.update({"X-CSRF-ID": csrf_token})
                self._is_authenticated = True
                return True
            return False
        except requests.exceptions.RequestException:
            return False
    
    def _get_status_data(self) -> Optional[dict]:
        """Fetch raw status data from the device."""
        status_url = f"{self.base_url}/status.cgi"
        try:
            response = self.session.get(status_url, timeout=15)
            if response.status_code in [401, 403]:
                return None
            response.raise_for_status()
            data = response.json()
            if "host" not in data:
                return None
            return data
        except (requests.exceptions.RequestException, ValueError):
            return None
    
    def get_status(self) -> DeviceStatus:
        """Fetch live status from the AirMAX device."""
        # Authenticate if needed
        if not self._is_authenticated:
            if not self._authenticate():
                return DeviceStatus(
                    host=self.host,
                    vendor=self.vendor,
                    role=DeviceRole.ACCESS_POINT,
                    is_online=False,
                    last_error="Authentication failed"
                )
        
        # Get data
        data = self._get_status_data()
        if data is None:
            # Try re-auth
            if not self._authenticate():
                return DeviceStatus(
                    host=self.host,
                    vendor=self.vendor,
                    role=DeviceRole.ACCESS_POINT,
                    is_online=False,
                    last_error="Session expired and re-auth failed"
                )
            data = self._get_status_data()
            if data is None:
                return DeviceStatus(
                    host=self.host,
                    vendor=self.vendor,
                    role=DeviceRole.ACCESS_POINT,
                    is_online=False,
                    last_error="Could not fetch status data"
                )
        
        # Parse the data
        host_info = data.get("host", {})
        wireless_info = data.get("wireless", {})
        interfaces = data.get("interfaces", [{}, {}])
        ath0_status = interfaces[1].get("status", {}) if len(interfaces) > 1 else {}
        gps_info = data.get("gps", {})
        throughput_info = wireless_info.get("throughput", {})
        polling_info = wireless_info.get("polling", {})
        
        # Parse connected clients
        clients = self._parse_clients(wireless_info.get("sta", []))
        
        return DeviceStatus(
            host=self.host,
            vendor=self.vendor,
            role="access_point",
            hostname=host_info.get("hostname"),
            model=host_info.get("devmodel"),
            mac=interfaces[1].get("hwaddr") if len(interfaces) > 1 else None,
            firmware=host_info.get("fwversion"),
            uptime=host_info.get("uptime"),
            is_online=True,
            frequency=wireless_info.get("frequency"),
            channel_width=wireless_info.get("chanbw"),
            essid=wireless_info.get("essid"),
            noise_floor=wireless_info.get("noisef"),
            client_count=wireless_info.get("count", 0),
            tx_bytes=ath0_status.get("tx_bytes"),
            rx_bytes=ath0_status.get("rx_bytes"),
            tx_throughput=throughput_info.get("tx"),
            rx_throughput=throughput_info.get("rx"),
            airtime_usage=polling_info.get("use"),
            gps_lat=gps_info.get("lat"),
            gps_lon=gps_info.get("lon"),
            clients=clients,
            extra={
                "airtime_tx": polling_info.get("tx_use"),
                "airtime_rx": polling_info.get("rx_use"),
                "gps_sats": gps_info.get("sats"),
            }
        )
    
    def _parse_clients(self, sta_list: list) -> List[ConnectedClient]:
        """Parse the station list from AirOS."""
        clients = []
        for cpe_data in sta_list:
            remote = cpe_data.get("remote", {})
            stats_data = cpe_data.get("stats", {})
            airmax = cpe_data.get("airmax", {})
            eth_info = remote.get("ethlist", [{}])[0] if remote.get("ethlist") else {}
            chainrssi = cpe_data.get("chainrssi", [None, None])
            
            clients.append(ConnectedClient(
                mac=cpe_data.get("mac"),
                hostname=remote.get("hostname"),
                ip_address=cpe_data.get("lastip"),
                signal=cpe_data.get("signal"),
                signal_chain0=chainrssi[0] if len(chainrssi) > 0 else None,
                signal_chain1=chainrssi[1] if len(chainrssi) > 1 else None,
                noisefloor=cpe_data.get("noisefloor"),
                tx_throughput_kbps=remote.get("tx_throughput"),
                rx_throughput_kbps=remote.get("rx_throughput"),
                tx_bytes=stats_data.get("tx_bytes"),
                rx_bytes=stats_data.get("rx_bytes"),
                uptime=remote.get("uptime"),
                extra={
                    "dl_capacity": airmax.get("dl_capacity"),
                    "ul_capacity": airmax.get("ul_capacity"),
                    "eth_plugged": eth_info.get("plugged"),
                    "eth_speed": eth_info.get("speed"),
                }
            ))
        return clients
    
    def get_connected_clients(self) -> List[ConnectedClient]:
        """Get the list of connected clients."""
        status = self.get_status()
        return status.clients
    
    def test_connection(self) -> bool:
        """Test if the device is reachable."""
        return self._authenticate()
    
    def disconnect(self):
        """Logout and close session."""
        try:
            logout_url = f"{self.base_url}/api/auth/logout"
            self.session.post(logout_url, timeout=10)
        except requests.exceptions.RequestException:
            pass
        finally:
            self.session.close()
            self._is_authenticated = False
