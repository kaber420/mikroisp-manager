# app/utils/device_clients/adapter_factory.py
"""
Adapter Factory.
Returns the appropriate device adapter based on vendor type.
"""

from typing import Optional
import logging

from .adapters.base import BaseDeviceAdapter
from .adapters.ubiquiti_airmax import UbiquitiAirmaxAdapter
from .adapters.mikrotik_wireless import MikrotikWirelessAdapter
from ...core.constants import DeviceVendor

logger = logging.getLogger(__name__)


# Default ports for each vendor
DEFAULT_PORTS = {
    DeviceVendor.UBIQUITI: 443,
    DeviceVendor.MIKROTIK: 8729,
}


def get_device_adapter(
    host: str,
    username: str,
    password: str,
    vendor: str = DeviceVendor.UBIQUITI,
    port: Optional[int] = None,
    **kwargs
) -> BaseDeviceAdapter:
    """
    Factory function to get the appropriate device adapter.
    
    Args:
        host: Device IP address or hostname
        username: Login username
        password: Login password
        vendor: Device vendor (DeviceVendor.UBIQUITI, DeviceVendor.MIKROTIK)
        port: API port (uses default if not specified)
        **kwargs: Additional vendor-specific options
    
    Returns:
        BaseDeviceAdapter instance for the specified vendor
    
    Raises:
        ValueError: If vendor is not supported
    """
    # Normalize vendor string (backwards compatible)
    vendor_normalized = vendor.lower() if isinstance(vendor, str) else vendor
    
    if port is None:
        port = DEFAULT_PORTS.get(vendor_normalized, 443)
    
    if vendor_normalized == DeviceVendor.UBIQUITI:
        use_https = kwargs.get("use_https", True)
        return UbiquitiAirmaxAdapter(
            host=host,
            username=username,
            password=password,
            port=port,
            use_https=use_https
        )
    
    elif vendor_normalized == DeviceVendor.MIKROTIK:
        return MikrotikWirelessAdapter(
            host=host,
            username=username,
            password=password,
            port=port
        )
    
    else:
        raise ValueError(f"Unsupported vendor: {vendor}. Supported: {DeviceVendor.UBIQUITI}, {DeviceVendor.MIKROTIK}")


def get_supported_vendors() -> list:
    """Returns list of supported vendor names."""
    return [DeviceVendor.UBIQUITI, DeviceVendor.MIKROTIK]

