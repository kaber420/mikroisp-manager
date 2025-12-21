# app/services/switch_service.py
"""
Service layer for Switch domain.
Handles device connections, CRUD operations, and status monitoring.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from ..db import switches_db
from ..utils.security import decrypt_data
from ..utils.device_clients.adapters.mikrotik_switch import MikrotikSwitchAdapter

logger = logging.getLogger(__name__)


class SwitchConnectionError(Exception):
    pass


class SwitchCommandError(Exception):
    pass


class SwitchService:
    """
    Service for interacting with a specific switch.
    Wraps the MikrotikSwitchAdapter and provides a clean interface for the API layer.
    """

    def __init__(self, host: str, switch_data: Dict[str, Any]):
        """
        Initialize the switch service.
        
        Args:
            host: The switch IP address/hostname
            switch_data: Dictionary containing switch credentials from database
        """
        self.host = host
        self.switch_data = switch_data
        self.adapter = None

        if not self.switch_data:
            raise SwitchConnectionError(f"Switch {host} no encontrado.")

        # Initialize the adapter
        password = switch_data.get("password", "")
        port = switch_data.get("api_ssl_port") or switch_data.get("api_port", 8728)
        
        self.adapter = MikrotikSwitchAdapter(
            host=self.host,
            username=switch_data.get("username", ""),
            password=password,
            port=port
        )

    def disconnect(self):
        """Close the adapter connection."""
        if self.adapter:
            try:
                self.adapter.disconnect()
            except Exception:
                pass
            self.adapter = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_api_client(self):
        """
        Devuelve el cliente API subyacente (RouterOsApi).
        Útil para servicios compartidos que necesitan acceso directo.
        """
        if not self.adapter:
            raise SwitchConnectionError("Adapter is not initialized")
        return self.adapter._get_api()

    # --- Status Methods ---
    
    def get_status(self) -> Dict[str, Any]:
        """Get current switch status (CPU, Memory, etc.)."""
        status = self.adapter.get_status()
        return status.to_dict() if hasattr(status, 'to_dict') else {
            "host": status.host,
            "vendor": status.vendor,
            "role": status.role,
            "hostname": status.hostname,
            "model": status.model,
            "firmware": status.firmware,
            "is_online": status.is_online,
            "last_error": status.last_error,
            "extra": status.extra
        }

    def get_system_resources(self) -> Dict[str, Any]:
        """Get detailed system resources."""
        return self.adapter.get_system_resources()

    def test_connection(self) -> bool:
        """Test if the switch is reachable."""
        return self.adapter.test_connection()

    # --- Port/Interface Methods ---

    def get_interfaces(self) -> List[Dict[str, Any]]:
        """Get all interfaces from the switch."""
        try:
            api = self.adapter._get_api()
            return api.get_resource("/interface").get()
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []

    def get_port_stats(self) -> List[Dict[str, Any]]:
        """Get port statistics."""
        return self.adapter.get_port_stats()

    def get_poe_status(self) -> List[Dict[str, Any]]:
        """Get PoE status for supported switches."""
        return self.adapter.get_poe_status()

    # --- Bridge/VLAN Methods (inherited from router) ---

    def get_bridges(self) -> List[Dict[str, Any]]:
        """Get all bridges configured on the switch."""
        try:
            api = self.adapter._get_api()
            return api.get_resource("/interface/bridge").get()
        except Exception as e:
            logger.error(f"Error getting bridges: {e}")
            return []

    def get_vlans(self) -> List[Dict[str, Any]]:
        """Get all VLANs configured on the switch."""
        try:
            api = self.adapter._get_api()
            return api.get_resource("/interface/vlan").get()
        except Exception as e:
            logger.error(f"Error getting VLANs: {e}")
            return []

    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str = ""):
        """Add a VLAN interface."""
        return self.adapter.add_vlan(name, vlan_id, interface, comment)

    def add_bridge(self, name: str, ports: List[str], comment: str = ""):
        """Add a bridge with ports."""
        return self.adapter.add_bridge(name, ports, comment)

    # --- Backup/System Methods ---

    def get_backup_files(self) -> List[Dict[str, Any]]:
        """Get list of backup files on the switch."""
        return self.adapter.get_backup_files()

    def create_backup(self, backup_name: str):
        """Create a backup file on the switch."""
        return self.adapter.create_backup(backup_name)


# --- CRUD Helper Functions ---

def get_all_switches() -> List[Dict[str, Any]]:
    """Get all switches from database."""
    return switches_db.get_all_switches()


def get_switch_by_host(host: str) -> Optional[Dict[str, Any]]:
    """Get switch by host from database."""
    return switches_db.get_switch_by_host(host)


def create_switch(switch_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new switch in database."""
    return switches_db.create_switch_in_db(switch_data)


def update_switch(host: str, switch_data: Dict[str, Any]) -> int:
    """Update switch in database."""
    return switches_db.update_switch_in_db(host, switch_data)


def delete_switch(host: str) -> int:
    """Delete switch from database."""
    return switches_db.delete_switch_from_db(host)


def get_enabled_switches() -> List[Dict[str, Any]]:
    """Get all enabled switches for monitoring."""
    return switches_db.get_enabled_switches_from_db()


# --- Dependency Injection Factory ---

def get_switch_service(host: str):
    """
    Factory function to create a SwitchService instance.
    Fetches switch data from DB and initializes the service.
    """
    switch_data = switches_db.get_switch_by_host(host)
    if not switch_data:
        raise SwitchConnectionError(f"Switch {host} no encontrado en la DB.")
    
    return SwitchService(host, switch_data)
