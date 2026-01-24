# app/services/switch_service.py
"""
Service layer for Switch domain.
Handles device connections, CRUD operations, and status monitoring.
Uses AsyncSession for database operations.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.switch import Switch
from ..utils.device_clients.adapters.mikrotik_switch import MikrotikSwitchAdapter
from ..utils.security import decrypt_data, encrypt_data

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

    def __init__(self, host: str, switch_data: dict[str, Any]):
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
            host=self.host, username=switch_data.get("username", ""), password=password, port=port
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

    def get_status(self) -> dict[str, Any]:
        """Get current switch status (CPU, Memory, etc.)."""
        status = self.adapter.get_status()
        return (
            status.to_dict()
            if hasattr(status, "to_dict")
            else {
                "host": status.host,
                "vendor": status.vendor,
                "role": status.role,
                "hostname": status.hostname,
                "model": status.model,
                "firmware": status.firmware,
                "is_online": status.is_online,
                "last_error": status.last_error,
                "extra": status.extra,
            }
        )

    def get_system_resources(self) -> dict[str, Any]:
        """Get detailed system resources."""
        return self.adapter.get_system_resources()

    def test_connection(self) -> bool:
        """Test if the switch is reachable."""
        return self.adapter.test_connection()

    # --- Port/Interface Methods ---

    def get_interfaces(self) -> list[dict[str, Any]]:
        """Get all interfaces from the switch."""
        try:
            api = self.adapter._get_api()
            return api.get_resource("/interface").get()
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []

    def get_port_stats(self) -> list[dict[str, Any]]:
        """Get port statistics."""
        return self.adapter.get_port_stats()

    def get_poe_status(self) -> list[dict[str, Any]]:
        """Get PoE status for supported switches."""
        return self.adapter.get_poe_status()

    # --- Bridge/VLAN Methods (inherited from router) ---

    def get_bridges(self) -> list[dict[str, Any]]:
        """Get all bridges configured on the switch."""
        try:
            api = self.adapter._get_api()
            return api.get_resource("/interface/bridge").get()
        except Exception as e:
            logger.error(f"Error getting bridges: {e}")
            return []

    def get_vlans(self) -> list[dict[str, Any]]:
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

    def add_bridge(self, name: str, ports: list[str], comment: str = ""):
        """Add a bridge with ports."""
        return self.adapter.add_bridge(name, ports, comment)

    # --- Backup/System Methods ---

    def get_backup_files(self) -> list[dict[str, Any]]:
        """Get list of backup files on the switch."""
        return self.adapter.get_backup_files()

    def create_backup(self, backup_name: str):
        """Create a backup file on the switch."""
        return self.adapter.create_backup(backup_name)

    # --- SSL/Certificate Management Methods ---

    def get_ssl_status(self) -> dict[str, Any]:
        """Check the SSL/TLS status of the switch."""
        return self.adapter.get_ssl_status()

    def ensure_ssl_provisioned(self) -> bool:
        """
        Checks if the switch has a valid/trusted SSL certificate.
        If not, automatically provisions one using PKIService.
        Returns True if provisioned (or already valid), False if failed.
        """
        from .pki_service import PKIService

        try:
            # 1. Check current Status
            status = self.adapter.get_ssl_status()

            # If already secure, we are good.
            if (
                status.get("ssl_enabled")
                and status.get("is_trusted")
                and status.get("status") == "secure"
            ):
                logger.info(f"Switch {self.host} SSL is ALREADY SECURE (Zero Trust Compliant).")
                return True

            logger.warning(
                f"Switch {self.host} SSL is INSECURE ({status.get('status')}). Auto-provisioning for Zero Trust..."
            )

            # 2. Generate Certs
            pki = PKIService()
            success, key_pem, cert_pem = pki.generate_full_cert_pair(self.host)

            if not success:
                logger.error(f"Failed to generate certificates for {self.host}")
                return False

            # 3. Import & Apply
            result = self.adapter.import_certificate(cert_pem, key_pem)

            if result.get("status") == "success":
                logger.info(
                    f"✅ Auto-provisioning successful for switch {self.host}. Connection secured."
                )
                return True
            else:
                logger.error(
                    f"❌ Auto-provisioning failed for switch {self.host}: {result.get('message')}"
                )
                return False

        except Exception as e:
            logger.error(f"Error in ensure_ssl_provisioned for switch {self.host}: {e}")
            import traceback

            traceback.print_exc()
            return False


# --- Async CRUD Helper Functions (with Session) ---


async def get_all_switches(session: AsyncSession) -> list[dict[str, Any]]:
    """Get all switches from database."""
    stmt = select(Switch).order_by(Switch.host)
    result = await session.exec(stmt)
    switches = result.all()

    output = []
    for s in switches:
        s_out = s.model_dump()
        # Don't expose passwords in list view
        s_out["password"] = None
        output.append(s_out)
    return output


async def get_switch_by_host(session: AsyncSession, host: str) -> dict[str, Any] | None:
    """Get switch by host from database."""
    switch = await session.get(Switch, host)
    if not switch:
        return None

    # Return a copy with decrypted password
    data = switch.model_dump()
    if data.get("password"):
        try:
            data["password"] = decrypt_data(data["password"])
        except Exception as e:
            logger.error(f"Error decrypting password for switch {host}: {e}")
    return data


async def create_switch(session: AsyncSession, switch_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new switch in database."""
    data = switch_data.copy()
    if "password" in data:
        data["password"] = encrypt_data(data["password"])

    switch = Switch(**data)
    session.add(switch)
    try:
        await session.commit()
        await session.refresh(switch)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Switch host (IP) '{switch_data.get('host')}' ya existe o error: {e}")

    return await get_switch_by_host(session, switch.host)


async def update_switch(session: AsyncSession, host: str, switch_data: dict[str, Any]) -> int:
    """Update switch in database."""
    switch = await session.get(Switch, host)
    if not switch:
        return 0

    clean_updates = switch_data.copy()
    if "password" in clean_updates and clean_updates["password"]:
        clean_updates["password"] = encrypt_data(clean_updates["password"])

    for key, value in clean_updates.items():
        if hasattr(switch, key):
            setattr(switch, key, value)

    session.add(switch)
    await session.commit()
    await session.refresh(switch)
    return 1


async def delete_switch(session: AsyncSession, host: str) -> int:
    """Delete switch from database."""
    switch = await session.get(Switch, host)
    if not switch:
        return 0
    await session.delete(switch)
    await session.commit()
    return 1


async def get_enabled_switches(session: AsyncSession) -> list[dict[str, Any]]:
    """Get all enabled switches for monitoring."""
    stmt = select(Switch).where(Switch.is_enabled == True)
    result = await session.exec(stmt)
    switches = result.all()

    output = []
    for s in switches:
        data = s.model_dump()
        if data.get("password"):
            try:
                data["password"] = decrypt_data(data["password"])
            except Exception:
                pass
        output.append(data)
    return output


# --- Dependency Injection Factory ---


async def get_switch_service(session: AsyncSession, host: str) -> SwitchService:
    """
    Factory function to create a SwitchService instance.
    Fetches switch data from DB and initializes the service.
    """
    switch_data = await get_switch_by_host(session, host)
    if not switch_data:
        raise SwitchConnectionError(f"Switch {host} no encontrado en la DB.")

    return SwitchService(host, switch_data)
