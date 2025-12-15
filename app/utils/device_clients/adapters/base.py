# app/utils/device_clients/adapters/base.py
"""
Base adapter interface for all device types.
All vendor-specific adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class ConnectedClient:
    """
    Represents a client connected to an AP (CPE/Station).
    This is a vendor-agnostic representation.
    """
    mac: str
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    signal: Optional[int] = None
    signal_chain0: Optional[int] = None
    signal_chain1: Optional[int] = None
    noisefloor: Optional[int] = None
    
    # Capacity/Quality metrics
    tx_rate: Optional[int] = None  # Mbps or Kbps depending on vendor
    rx_rate: Optional[int] = None
    ccq: Optional[int] = None  # MikroTik Client Connection Quality (%)
    
    # Throughput
    tx_bytes: Optional[int] = None
    rx_bytes: Optional[int] = None
    tx_throughput_kbps: Optional[int] = None
    rx_throughput_kbps: Optional[int] = None
    
    # Connection info
    uptime: Optional[int] = None  # seconds
    interface: Optional[str] = None  # Which interface they're connected to
    
    # Extra vendor-specific data
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceStatus:
    """
    Represents the live status of a device (AP or Switch).
    This is a vendor-agnostic representation.
    """
    host: str
    vendor: str
    role: str  # "access_point" or "switch"
    
    # Device info
    hostname: Optional[str] = None
    model: Optional[str] = None
    mac: Optional[str] = None
    firmware: Optional[str] = None
    uptime: Optional[int] = None  # seconds
    
    # Status
    is_online: bool = True
    last_error: Optional[str] = None
    
    # Wireless info (for APs)
    frequency: Optional[int] = None
    channel_width: Optional[int] = None
    essid: Optional[str] = None
    noise_floor: Optional[int] = None
    client_count: int = 0
    
    # Traffic
    tx_bytes: Optional[int] = None
    rx_bytes: Optional[int] = None
    tx_throughput: Optional[int] = None  # Kbps
    rx_throughput: Optional[int] = None  # Kbps
    
    # Airtime (Ubiquiti) or similar metrics
    airtime_usage: Optional[int] = None
    
    # GPS (if available)
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    
    # Connected clients
    clients: List[ConnectedClient] = field(default_factory=list)
    
    # Extra vendor-specific data
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseDeviceAdapter(ABC):
    """
    Abstract base class for all device adapters.
    Each vendor (Ubiquiti, MikroTik, etc.) must implement this interface.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 443):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
    
    @property
    @abstractmethod
    def vendor(self) -> str:
        """Returns the vendor name (e.g., 'ubiquiti', 'mikrotik')."""
        pass
    
    @abstractmethod
    def get_status(self) -> DeviceStatus:
        """
        Fetches the live status of the device.
        Returns a DeviceStatus object with all available information.
        """
        pass
    
    @abstractmethod
    def get_connected_clients(self) -> List[ConnectedClient]:
        """
        Fetches the list of connected clients/stations.
        For APs this is the registration table, for switches this could be MAC table.
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Tests if the device is reachable and credentials are valid.
        Returns True if connection is successful, False otherwise.
        """
        pass
    
    def disconnect(self):
        """
        Cleanup method to close any open connections.
        Override if the adapter maintains persistent connections.
        """
        pass
