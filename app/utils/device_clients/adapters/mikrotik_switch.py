# app/utils/device_clients/adapters/mikrotik_switch.py
"""
MikroTik Switch Adapter - Inherits 100% functionality from MikrotikRouterAdapter.
Switches run RouterOS and support all standard router operations.
This adapter can be extended in the future for switch-specific features like
port management, VLANs, and spanning tree.
"""
import logging
from typing import Dict, Any, List, Optional
from routeros_api.api import RouterOsApi

from .mikrotik_router import MikrotikRouterAdapter
from .base import DeviceStatus

logger = logging.getLogger(__name__)


class MikrotikSwitchAdapter(MikrotikRouterAdapter):
    """
    Adapter for MikroTik Switches.
    Inherits all RouterOS functionality from MikrotikRouterAdapter.
    
    Switches (like CRS series) run full RouterOS and support:
    - System resources monitoring
    - Interface management
    - Bridge and VLAN configuration
    - User management
    - Backup and file operations
    
    Future switch-specific features could include:
    - Port statistics
    - PoE management
    - Spanning Tree status
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 8729, api: Optional[RouterOsApi] = None):
        super().__init__(host, username, password, port, api)

    @property
    def role(self) -> str:
        """Device role identifier."""
        return "switch"

    def get_status(self) -> DeviceStatus:
        """
        Get basic status for a Switch.
        Overrides parent to set correct role.
        """
        status = super().get_status()
        # Update the role to 'switch' for proper identification
        return DeviceStatus(
            host=status.host,
            vendor=status.vendor,
            role="switch",
            hostname=status.hostname,
            model=status.model,
            firmware=status.firmware,
            is_online=status.is_online,
            last_error=status.last_error,
            extra=status.extra
        )

    # --- Switch-Specific Methods (Future Extensions) ---
    
    def get_port_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all switch ports.
        Returns interface statistics filtered for ethernet ports.
        """
        try:
            api = self._get_api()
            interfaces = api.get_resource("/interface/ethernet").get()
            return interfaces
        except Exception as e:
            logger.error(f"Error getting port stats: {e}")
            return []

    def get_poe_status(self) -> List[Dict[str, Any]]:
        """
        Get PoE status for switch ports (if supported).
        Returns empty list if PoE is not available on this switch.
        """
        try:
            api = self._get_api()
            poe_out = api.get_resource("/interface/ethernet/poe").get()
            return poe_out
        except Exception as e:
            # PoE may not be supported on all switches
            logger.debug(f"PoE not available or error: {e}")
            return []

    def get_switch_chip_ports(self) -> List[Dict[str, Any]]:
        """
        Get switch chip port configuration.
        Available on CRS series switches.
        """
        try:
            api = self._get_api()
            ports = api.get_resource("/interface/ethernet/switch/port").get()
            return ports
        except Exception as e:
            logger.debug(f"Switch chip ports not available: {e}")
            return []
