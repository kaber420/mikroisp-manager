# app/services/monitor_service.py
import logging
from typing import Any

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
    def get_active_devices(self):
        """Recupera todos los dispositivos habilitados para monitorear."""
        return {
            "aps": get_enabled_aps_for_monitor(),
            "routers": get_enabled_routers_from_db(),
        }

    def check_ap(self, ap_config: dict[str, Any]):
        """Verifica el estado de un AP usando adaptadores, guarda estadísticas y envía alertas."""
        host = ap_config["host"]
        vendor = ap_config.get("vendor", DeviceVendor.UBIQUITI)
        logger.info(f"--- Verificando AP en {host} (vendor: {vendor}) ---")

        try:
            # Get the appropriate adapter based on vendor
            port = ap_config.get("api_port") or (443 if vendor == DeviceVendor.UBIQUITI else 8729)

            adapter = get_device_adapter(
                host=host,
                username=ap_config["username"],
                password=ap_config["password"],
                vendor=vendor,
                port=port,
            )

            try:
                status = adapter.get_status()
                previous_status = get_ap_status(host)

                if status and status.is_online:
                    current_status = DeviceStatus.ONLINE
                    hostname = status.hostname or host
                    logger.info(f"Estado de '{hostname}' ({host}): ONLINE")

                    # Save stats using the new vendor-agnostic function
                    save_device_stats(host, status, vendor=vendor)

                    # Update AP status
                    update_ap_status(
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
                        add_event_log(
                            host,
                            "ap",
                            "success",
                            f"El AP {hostname} ({host}) está en línea nuevamente.",
                        )
                        send_telegram_alert(message)
                else:
                    self._handle_offline_ap(host, get_ap_status(host))
            finally:
                adapter.disconnect()

        except Exception as e:
            logger.error(f"Error procesando AP {host}: {e}")
            # Asumimos offline si falla drásticamente la conexión
            self._handle_offline_ap(host, get_ap_status(host))

    def _handle_offline_ap(self, host: str, previous_status: str):
        logger.warning(f"Estado de {host}: OFFLINE")
        update_ap_status(host, DeviceStatus.OFFLINE)

        if previous_status != DeviceStatus.OFFLINE:
            ap_info = get_ap_by_host_with_stats(host)
            hostname = ap_info.get("hostname") if (ap_info and ap_info.get("hostname")) else host
            message = f"❌ *ALERTA: AP CAÍDO*\n\nNo se pudo establecer conexión con el AP *{hostname}* (`{host}`)."
            add_event_log(host, "ap", "danger", f"El AP {hostname} ({host}) ha perdido conexión.")
            send_telegram_alert(message)

    def check_router(self, router_config: dict[str, Any]):
        """Verifica el estado de un Router, actualiza recursos y envía alertas."""
        host = router_config["host"]
        logger.info(f"--- Verificando Router en {host} ---")

        status_data = None
        try:
            # Create Router model from config (which has decrypted password)
            router_creds = Router(**router_config)

            with RouterService(
                host, router_creds, decrypted_password=router_config["password"]
            ) as router_service:
                status_data = router_service.get_system_resources()

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

        previous_status = get_router_status(host)

        if status_data:
            current_status = DeviceStatus.ONLINE
            hostname = status_data.get("name", host)
            logger.info(f"Estado de Router '{hostname}' ({host}): ONLINE")

            update_router_status(host, current_status, data=status_data)

            if previous_status == DeviceStatus.OFFLINE:
                message = f"✅ *ROUTER RECUPERADO*\n\nEl Router *{hostname}* (`{host}`) ha vuelto a estar en línea."
                add_event_log(host, "router", "success", f"Router {hostname} ({host}) recuperado.")
                send_telegram_alert(message)
        else:
            current_status = DeviceStatus.OFFLINE
            logger.warning(f"Estado de Router {host}: OFFLINE")

            update_router_status(host, current_status)

            if previous_status != DeviceStatus.OFFLINE:
                router_info = get_router_by_host(host)
                hostname = (
                    router_info.get("hostname")
                    if (router_info and router_info.get("hostname"))
                    else host
                )

                message = f"❌ *ALERTA: ROUTER CAÍDO*\n\nNo se pudo establecer conexión API-SSL con el Router *{hostname}* (`{host}`)."
                add_event_log(
                    host,
                    "router",
                    "danger",
                    f"Router {hostname} ({host}) ha dejado de responder.",
                )
                send_telegram_alert(message)
