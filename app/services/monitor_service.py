
import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.constants import DeviceStatus, DeviceVendor
from ..db.aps_db import (
    get_ap_by_host_with_stats,
    get_ap_status,
    get_enabled_aps_for_monitor,
    update_ap_status,
)
from ..db.logs_db import add_event_log
from ..db.router_db import (
    get_enabled_routers_from_db,
    get_router_by_host,
    get_router_status,
    update_router_status,
)
from ..db.stats_db import save_device_stats
from ..models.ap import AP
from ..models.router import Router
from ..services.router_service import (
    RouterCommandError,
    RouterConnectionError,
    RouterNotProvisionedError,
    RouterService,
)
from ..utils.alerter import send_telegram_alert
from ..utils.device_clients.adapter_factory import get_device_adapter

logger = logging.getLogger(__name__)


class MonitorService:
    async def get_active_devices(self, session: AsyncSession):
        """Recupera todos los dispositivos habilitados para monitorear."""
        # Run in parallel
        aps, routers = await asyncio.gather(
            get_enabled_aps_for_monitor(session),
            get_enabled_routers_from_db(session)
        )
        return {
            "aps": aps,
            "routers": routers,
        }

    async def check_ap(self, session: AsyncSession, ap: AP):
        """Verifica el estado de un AP usando adaptadores, guarda estadísticas y envía alertas."""
        host = ap.host
        vendor = ap.vendor or DeviceVendor.UBIQUITI
        logger.info(f"--- Verificando AP en {host} (vendor: {vendor}) ---")

        try:
            # Get the appropriate adapter based on vendor
            port = ap.api_port or (443 if vendor == DeviceVendor.UBIQUITI else 8729)

            # Wrapper for blocking network call
            def do_network_check():
                adapter = get_device_adapter(
                    host=host,
                    username=ap.username,
                    password=ap.password,
                    vendor=vendor,
                    port=port,
                )
                try:
                    return adapter.get_status()
                finally:
                    adapter.disconnect()

            # Run network check in thread
            status = await asyncio.to_thread(do_network_check)
            previous_status = await get_ap_status(session, host)

            if status and status.is_online:
                current_status = DeviceStatus.ONLINE
                hostname = status.hostname or host
                logger.info(f"Estado de '{hostname}' ({host}): ONLINE")

                # Save stats (stats_db is likely sync)
                await asyncio.to_thread(save_device_stats, host, status, vendor=vendor)

                # Update AP status (async)
                await update_ap_status(
                    session,
                    host,
                    current_status,
                    data={
                        "hostname": status.hostname,
                        "model": status.model,
                        "firmware": status.firmware,
                        "mac": status.mac,
                    },
                )

                if previous_status == DeviceStatus.OFFLINE:
                    message = f"✅ *AP RECUPERADO*\n\nEl AP *{hostname}* (`{host}`) ha vuelto a estar en línea."
                    await asyncio.to_thread(add_event_log, host, "ap", "success", f"El AP {hostname} ({host}) está en línea nuevamente.")
                    await asyncio.to_thread(send_telegram_alert, message)
            else:
                await self._handle_offline_ap(session, host, previous_status)

        except Exception as e:
            logger.error(f"Error procesando AP {host}: {e}")
            prev_stat = await get_ap_status(session, host)
            await self._handle_offline_ap(session, host, prev_stat)

    async def _handle_offline_ap(self, session: AsyncSession, host: str, previous_status: str):
        logger.warning(f"Estado de {host}: OFFLINE")
        await update_ap_status(session, host, DeviceStatus.OFFLINE)

        if previous_status != DeviceStatus.OFFLINE:
            ap_info = await get_ap_by_host_with_stats(session, host)
            hostname = ap_info.get("hostname") if (ap_info and ap_info.get("hostname")) else host
            message = f"❌ *ALERTA: AP CAÍDO*\n\nNo se pudo establecer conexión con el AP *{hostname}* (`{host}`)."
            await asyncio.to_thread(add_event_log, host, "ap", "danger", f"El AP {hostname} ({host}) ha perdido conexión.")
            await asyncio.to_thread(send_telegram_alert, message)

    async def check_router(self, session: AsyncSession, router: Router):
        """Verifica el estado de un Router, actualiza recursos y envía alertas."""
        host = router.host
        logger.info(f"--- Verificando Router en {host} ---")

        status_data = None
        try:
            def do_network_check():
                with RouterService(
                    host, router, decrypted_password=router.password
                ) as router_service:
                    return router_service.get_system_resources()

            status_data = await asyncio.to_thread(do_network_check)

        except (
            RouterConnectionError,
            RouterCommandError,
            RouterNotProvisionedError,
        ) as e:
            logger.warning(f"No se pudo obtener el estado del Router {host}: {e}")
            status_data = None
        except Exception as e:
            logger.error(f"Error inesperado en Router {host}: {e}")
            status_data = None

        previous_status = await get_router_status(session, host)

        if status_data:
            current_status = DeviceStatus.ONLINE
            hostname = status_data.get("name", host)
            logger.info(f"Estado de Router '{hostname}' ({host}): ONLINE")

            await update_router_status(session, host, current_status, data=status_data)

            if previous_status == DeviceStatus.OFFLINE:
                message = f"✅ *ROUTER RECUPERADO*\n\nEl Router *{hostname}* (`{host}`) ha vuelto a estar en línea."
                await asyncio.to_thread(add_event_log, host, "router", "success", f"Router {hostname} ({host}) recuperado.")
                await asyncio.to_thread(send_telegram_alert, message)
        else:
            current_status = DeviceStatus.OFFLINE
            logger.warning(f"Estado de Router {host}: OFFLINE")

            await update_router_status(session, host, current_status)

            if previous_status != DeviceStatus.OFFLINE:
                router_info = await get_router_by_host(session, host)
                hostname = router_info.hostname if (router_info and router_info.hostname) else host

                message = f"❌ *ALERTA: ROUTER CAÍDO*\n\nNo se pudo establecer conexión API-SSL con el Router *{hostname}* (`{host}`)."
                await asyncio.to_thread(add_event_log,
                    host,
                    "router",
                    "danger",
                    f"Router {hostname} ({host}) ha dejado de responder.",
                )
                await asyncio.to_thread(send_telegram_alert, message)
