# app/utils/device_clients/adapters/base.py
"""
Base adapter interface for all device types.
All vendor-specific adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectedClient:
    """
    Represents a client connected to an AP (CPE/Station).
    This is a vendor-agnostic representation.
    """

    mac: str
    hostname: str | None = None
    ip_address: str | None = None
    signal: int | None = None
    signal_chain0: int | None = None
    signal_chain1: int | None = None
    noisefloor: int | None = None

    # Capacity/Quality metrics
    tx_rate: int | None = None  # Mbps or Kbps depending on vendor
    rx_rate: int | None = None
    ccq: int | None = None  # MikroTik Client Connection Quality (%)

    # Throughput
    tx_bytes: int | None = None
    rx_bytes: int | None = None
    tx_throughput_kbps: int | None = None
    rx_throughput_kbps: int | None = None

    # Connection info
    uptime: int | None = None  # seconds
    interface: str | None = None  # Which interface they're connected to
    ssid: str | None = None  # SSID of the network (ROS7 wifi)
    band: str | None = None  # Band (2ghz, 5ghz, etc.)

    # Extra vendor-specific data
    extra: dict[str, Any] = field(default_factory=dict)


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
    hostname: str | None = None
    model: str | None = None
    mac: str | None = None
    firmware: str | None = None
    uptime: int | None = None  # seconds

    # Status
    is_online: bool = True
    last_error: str | None = None

    # Wireless info (for APs)
    frequency: int | None = None
    channel_width: int | None = None
    essid: str | None = None
    noise_floor: int | None = None
    client_count: int = 0

    # Traffic
    tx_bytes: int | None = None
    rx_bytes: int | None = None
    tx_throughput: int | None = None  # Kbps
    rx_throughput: int | None = None  # Kbps

    # Airtime (Ubiquiti) or similar metrics
    airtime_usage: int | None = None

    # GPS (if available)
    gps_lat: float | None = None
    gps_lon: float | None = None

    # Connected clients
    clients: list[ConnectedClient] = field(default_factory=list)

    # Extra vendor-specific data
    extra: dict[str, Any] = field(default_factory=dict)

    # List of all wireless interfaces (for dual-band APs)
    # format: [{name, band, frequency, ssid, tx_power, ...}, ...]
    interfaces: list[dict[str, Any]] = field(default_factory=list)


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
    def get_connected_clients(self) -> list[ConnectedClient]:
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
