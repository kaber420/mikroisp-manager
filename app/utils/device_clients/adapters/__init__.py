# app/utils/device_clients/adapters/__init__.py
"""
Device Adapters package.
Contains vendor-specific adapters for APs and Switches.
"""

from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
from .ubiquiti_airmax import UbiquitiAirmaxAdapter
from .mikrotik_wireless import MikrotikWirelessAdapter, remove_cached_pool

__all__ = [
    "BaseDeviceAdapter",
    "DeviceStatus",
    "ConnectedClient",
    "UbiquitiAirmaxAdapter",
    "MikrotikWirelessAdapter",
    "remove_cached_pool",
]


