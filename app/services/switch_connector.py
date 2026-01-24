import asyncio
import logging
from datetime import datetime

from ..db.engine import async_session_maker
from ..models.switch import Switch
from ..utils.security import decrypt_data
from .mikrotik_base_connector import MikrotikBaseConnector
from sqlmodel import select

logger = logging.getLogger(__name__)


class SwitchConnector(MikrotikBaseConnector):
    """
    Switch specific connector.
    """

    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Subscribe to a switch.
        Overridden to fetch credentials from DB as per original implementation.
        """
        # Get full switch data from DB using async session
        async with async_session_maker() as session:
            switch = await session.get(Switch, host)
            if not switch:
                self.logger.error(f"Switch {host} not found in DB")
                raise ValueError(f"Switch {host} not found")

            # Prepare switch_data dict with decrypted password
            switch_data = switch.model_dump()
            if switch_data.get("password"):
                try:
                    switch_data["password"] = decrypt_data(switch_data["password"])
                except Exception:
                    pass

        # Call base subscribe with the fetched data
        # switch_data is expected to contain username/password
        await super().subscribe(host, switch_data)

    def fetch_switch_stats(self, host: str) -> dict:
        """
        Fetch monitoring statistics from a switch.
        """
        try:
            with self.api_session(host) as api:
                # Execute /system/resource
                resource_list = api.get_resource("/system/resource").get()
                if not resource_list:
                    return {"error": "No data from /system/resource"}

                r = resource_list[0]

                # Execute /system/identity
                identity_list = []
                try:
                    identity_list = api.get_resource("/system/identity").get()
                except Exception:
                    pass

                hostname = identity_list[0].get("name") if identity_list else None

                return {
                    "cpu_load": r.get("cpu-load"),
                    "free_memory": r.get("free-memory"),
                    "total_memory": r.get("total-memory"),
                    "uptime": r.get("uptime"),
                    "version": r.get("version"),
                    "board_name": r.get("board-name"),
                    "name": hostname,
                    "hostname": hostname,
                    "total_disk": r.get("total-hdd-space", r.get("total-disk-space")),
                    "free_disk": r.get("free-hdd-space", r.get("free-disk-space")),
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"Error fetching stats from {host}: {e}")
            return {"error": str(e)}


# Singleton instance
switch_connector = SwitchConnector()
