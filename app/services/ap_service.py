
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from ..api.aps.models import (
    APCreate,
    APHistoryResponse,
    APLiveDetail,
    APUpdate,
    CPEDetail,
    HistoryDataPoint,
)
from ..core.constants import DeviceStatus, DeviceVendor
from ..db import stats_db, aps_db
from ..models.ap import AP
from ..models.stats import APStats
from ..utils.device_clients.adapter_factory import get_device_adapter
from ..utils.device_clients.mikrotik import wireless as mikrotik_wireless
from ..utils.security import decrypt_data, encrypt_data


# --- Excepciones personalizadas del Servicio ---
class APNotFoundError(Exception):
    pass


class APUnreachableError(Exception):
    pass


class APDataError(Exception):
    pass


class APCreateError(Exception):
    pass


class APService:
    """
    Servicio para toda la lógica de negocio relacionada con los Access Points (APs).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_aps(self) -> list[dict[str, Any]]:
        """Obtiene todos los APs con sus últimas estadísticas."""
        # Use centralized logic from aps_db
        return await aps_db.get_all_aps_with_stats(self.session)

    # _fetch_latest_stats_map is no longer needed

    async def get_ap_by_host(self, host: str) -> dict[str, Any]:
        """Obtiene un AP específico por host."""
        ap_dict = await aps_db.get_ap_by_host_with_stats(self.session, host)
        if not ap_dict:
            raise APNotFoundError(f"AP no encontrado: {host}")

        # Decrypt password for service usage (if needed by caller, though risky to return in API)
        # The legacy service returned it decrypted.
        if ap_dict.get("password"):
            try:
                ap_dict["password"] = decrypt_data(ap_dict["password"])
            except Exception:
                pass
        
        return ap_dict

    # _fetch_latest_stats_for_host is no longer needed

    async def create_ap(self, ap_data: APCreate) -> dict[str, Any]:
        """Crea un nuevo AP en la base de datos."""
        ap_dict = ap_data.model_dump()

        if ap_dict.get("monitor_interval") is None:
            from ..models.setting import Setting
            
            setting = await self.session.get(Setting, "default_monitor_interval")
            default_interval_str = setting.value if setting else None
            
            ap_dict["monitor_interval"] = (
                int(default_interval_str)
                if default_interval_str and default_interval_str.isdigit()
                else 300
            )

        try:
            # Encrypt password
            if "password" in ap_dict:
                ap_dict["password"] = encrypt_data(ap_dict["password"])

            new_ap = AP(**ap_dict)
            self.session.add(new_ap)
            await self.session.commit()
            await self.session.refresh(new_ap)

            return await self.get_ap_by_host(new_ap.host)
        except Exception as e:
            raise APCreateError(str(e))

    async def update_ap(self, host: str, ap_update: APUpdate) -> dict[str, Any]:
        """Actualiza un AP existente."""
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado para actualizar: {host}")

        update_fields = ap_update.model_dump(exclude_unset=True)
        if not update_fields:
            raise APDataError("No se proporcionaron campos para actualizar.")

        if "password" in update_fields:
            if not update_fields["password"]:
                del update_fields["password"]
            else:
                update_fields["password"] = encrypt_data(update_fields["password"])

        for key, value in update_fields.items():
            setattr(ap, key, value)

        self.session.add(ap)
        await self.session.commit()
        await self.session.refresh(ap)

        return await self.get_ap_by_host(host)

    async def delete_ap(self, host: str):
        """Elimina un AP de la base de datos."""
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado para eliminar: {host}")

        await self.session.delete(ap)
        await self.session.commit()

    async def sync_cpe_names(self, host: str) -> dict[str, Any]:
        """
        Synchronizes CPE hostnames by fetching ARP table from the AP.
        """
        from ..models.cpe import CPE
        
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado: {host}")

        if ap.vendor != DeviceVendor.MIKROTIK:
            return {"synced_count": 0, "message": "Sync only available for MikroTik APs"}

        password = decrypt_data(ap.password)
        port = ap.api_port or 8729

        adapter = get_device_adapter(
            host=host,
            username=ap.username,
            password=password,
            vendor=ap.vendor,
            port=port,
        )

        try:
            api = adapter._get_api()
            clients_data = mikrotik_wireless.get_connected_clients(api, fetch_arp=True)
            
            now = datetime.utcnow()
            synced_count = 0
            
            for client in clients_data:
                mac = client.get("mac")
                hostname = client.get("hostname")
                ip_address = client.get("ip_address")
                
                if mac:
                    existing_cpe = await self.session.get(CPE, mac)
                    if existing_cpe:
                        if hostname:
                            existing_cpe.hostname = hostname
                        if ip_address:
                            existing_cpe.ip_address = ip_address
                        existing_cpe.last_seen = now
                        existing_cpe.status = "active"
                        self.session.add(existing_cpe)
                    else:
                        new_cpe = CPE(
                            mac=mac,
                            hostname=hostname,
                            ip_address=ip_address,
                            last_seen=now,
                            first_seen=now,
                            status="active"
                        )
                        self.session.add(new_cpe)
                    
                    if hostname:
                        synced_count += 1
            
            await self.session.commit()
            
            return {
                "synced_count": synced_count,
                "total_clients": len(clients_data),
                "clients": [
                    {"mac": c.get("mac"), "hostname": c.get("hostname"), "ip": c.get("ip_address")}
                    for c in clients_data
                ]
            }
        except Exception as e:
            await self.session.rollback()
            raise APUnreachableError(f"Error syncing CPE names for {host}: {e}")
        finally:
            adapter.disconnect()

    async def get_cpes_for_ap(self, host: str) -> list[dict[str, Any]]:
        """Obtiene los CPEs conectados a un AP desde el último snapshot."""
        result = await stats_db.get_cpes_for_ap_from_stats(self.session, host)
        return result if result else []

    async def get_live_data(self, host: str) -> APLiveDetail:
        """Obtiene datos en vivo de un AP y los formatea."""
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado en el inventario: {host}")

        password = decrypt_data(ap.password)
        vendor = ap.vendor or DeviceVendor.UBIQUITI
        port = ap.api_port or (443 if vendor == DeviceVendor.UBIQUITI else 8729)

        adapter = get_device_adapter(
            host=host,
            username=ap.username,
            password=password,
            vendor=vendor,
            port=port,
        )

        try:
            status = adapter.get_status()

            if not status.is_online:
                raise APUnreachableError(
                    f"No se pudo obtener datos del AP {host}. Error: {status.last_error}"
                )

            clients_list = []
            for client in status.clients:
                clients_list.append(
                    CPEDetail(
                        cpe_mac=client.mac,
                        cpe_hostname=client.hostname,
                        ip_address=client.ip_address,
                        signal=client.signal,
                        signal_chain0=client.signal_chain0,
                        signal_chain1=client.signal_chain1,
                        noisefloor=client.noisefloor,
                        dl_capacity=client.extra.get("dl_capacity"),
                        ul_capacity=client.extra.get("ul_capacity"),
                        throughput_rx_kbps=client.rx_throughput_kbps,
                        throughput_tx_kbps=client.tx_throughput_kbps,
                        total_rx_bytes=client.rx_bytes,
                        total_tx_bytes=client.tx_bytes,
                        cpe_uptime=client.uptime,
                        eth_plugged=client.extra.get("eth_plugged"),
                        eth_speed=client.extra.get("eth_speed"),
                        ccq=client.ccq,
                        tx_rate=client.tx_rate,
                        rx_rate=client.rx_rate,
                    )
                )

            extra_data = dict(status.extra) if status.extra else {}
            # (Memory usage calculation logic skipped/assumed mostly presentation)
             # Calculate memory usage percentage for MikroTik (Adding back as it's useful)
            if extra_data.get("free_memory") and extra_data.get("total_memory"):
                try:
                    free = int(extra_data["free_memory"])
                    total = int(extra_data["total_memory"])
                    if total > 0:
                        used = total - free
                        extra_data["memory_usage"] = round((used / total) * 100, 1)
                except (ValueError, TypeError):
                    pass
                    
            if status.uptime:
                uptime_secs = status.uptime
                days = uptime_secs // 86400
                hours = (uptime_secs % 86400) // 3600
                minutes = (uptime_secs % 3600) // 60
                
                # Simplified formatting
                parts = []
                if days > 0: parts.append(f"{days}d")
                if hours > 0: parts.append(f"{hours}h")
                parts.append(f"{minutes}m")
                extra_data["uptime"] = " ".join(parts)


            return APLiveDetail(
                host=host,
                username=ap.username,
                is_enabled=True,
                hostname=status.hostname,
                model=status.model,
                mac=status.mac,
                firmware=status.firmware,
                last_status=DeviceStatus.ONLINE,
                client_count=status.client_count,
                noise_floor=status.noise_floor,
                chanbw=status.channel_width,
                frequency=status.frequency,
                essid=status.essid,
                total_tx_bytes=status.tx_bytes,
                total_rx_bytes=status.rx_bytes,
                gps_lat=status.gps_lat,
                gps_lon=status.gps_lon,
                gps_sats=status.extra.get("gps_sats") if status.extra else None,
                total_throughput_tx=status.tx_throughput,
                total_throughput_rx=status.rx_throughput,
                airtime_total_usage=status.airtime_usage,
                airtime_tx_usage=status.extra.get("airtime_tx") if status.extra else None,
                airtime_rx_usage=status.extra.get("airtime_rx") if status.extra else None,
                clients=clients_list,
                vendor=vendor,
                extra=extra_data if extra_data else None,
            )
        finally:
            adapter.disconnect()

    async def get_wireless_interfaces(self, host: str) -> list[dict[str, str]]:
        # Copy-paste implementation but with async session if needed (it already used session so it's fine)
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado: {host}")

        vendor = ap.vendor or DeviceVendor.UBIQUITI
        if vendor != DeviceVendor.MIKROTIK:
            return []

        password = decrypt_data(ap.password)
        port = ap.api_port or 8729

        adapter = get_device_adapter(
            host=host,
            username=ap.username,
            password=password,
            vendor=vendor,
            port=port,
        )

        try:
            api = adapter._get_api()
            detailed = mikrotik_wireless.get_wireless_interfaces_detailed(api)
            return [
                {
                    "name": i["name"],
                    "type": i["type"],
                    "band": i["band"],
                    "frequency": str(i["frequency"]) if i.get("frequency") else None,
                    "channel_width": str(i.get("width")) if i.get("width") else None,
                    "ssid": (
                        i.get("ssid")
                        or i.get("original_record", {}).get("configuration.ssid")
                        or i.get("original_record", {}).get("ssid")
                        or None
                    ),
                    "tx_power": i.get("tx_power"),
                    "mac": i.get("original_record", {}).get("mac-address"),
                    "disabled": i.get("original_record", {}).get("disabled") == "true",
                    "running": i.get("original_record", {}).get("running") == "true",
                }
                for i in detailed
            ]
        except Exception as e:
            error_msg = str(e).lower()
            if "ssl" in error_msg or "handshake" in error_msg:
                raise APUnreachableError(f"Error de conexión SSL al AP {host}: {e}")
            raise APUnreachableError(f"No se pudo conectar al AP {host}: {e}")
        finally:
            adapter.disconnect()

    async def get_ap_history(self, host: str, period: str = "24h") -> APHistoryResponse:
        """Obtiene datos históricos de un AP desde la DB de estadísticas."""
        ap_info = await aps_db.get_ap_by_host_with_stats(self.session, host)
        hostname = ap_info.get("hostname", host) if ap_info else host

        # Calculate time
        from datetime import timedelta
        if period == "7d":
            delta = timedelta(days=7)
        elif period == "30d":
            delta = timedelta(days=30)
        else:
            delta = timedelta(hours=24)
        
        start_time = datetime.utcnow() - delta

        try:
            # Stats Query using APStats model
            stmt = select(APStats).where(
                APStats.ap_host == host, 
                APStats.timestamp >= start_time
            ).order_by(APStats.timestamp.asc())
            
            result = await self.session.exec(stmt)
            rows = result.all()
            
            # Map APStats model to HistoryDataPoint
            history_points = []
            for row in rows:
                history_points.append(HistoryDataPoint(
                    timestamp=row.timestamp,
                    client_count=row.client_count,
                    airtime_total_usage=row.airtime_total_usage,
                    total_throughput_tx=row.total_throughput_tx,
                    total_throughput_rx=row.total_throughput_rx
                ))

            return APHistoryResponse(
                host=host,
                hostname=hostname,
                history=history_points,
            )
        except Exception as e:
            raise APDataError(f"Error en la base de datos de estadísticas: {e}")
