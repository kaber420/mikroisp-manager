# app/utils/device_clients/adapters/__init__.py
"""
Device Adapters package.
Contains vendor-specific adapters for APs and Switches.
"""

from .base import BaseDeviceAdapter, ConnectedClient, DeviceStatus
from .mikrotik_wireless import MikrotikWirelessAdapter
from .ubiquiti_airmax import UbiquitiAirmaxAdapter

__all__ = [
    "BaseDeviceAdapter",
    "DeviceStatus",
    "ConnectedClient",
    "UbiquitiAirmaxAdapter",
    "MikrotikWirelessAdapter",
]
