# app/services/ap_service.py
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Importaciones de nuestras utilidades y capas de DB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from ..models.ap import AP
from ..utils.security import encrypt_data, decrypt_data
from ..utils.device_clients.adapter_factory import get_device_adapter
from ..utils.device_clients.adapters.base import DeviceStatus, ConnectedClient
from ..db import settings_db, stats_db
from ..db.base import get_stats_db_connection
from ..utils.device_clients.mikrotik import wireless as mikrotik_wireless
from ..core.constants import DeviceVendor, DeviceStatus

from ..api.aps.models import (
    AP as APResponse, # Renamed to avoid conflict with DB model
    APLiveDetail,
    CPEDetail,
    APHistoryResponse,
    HistoryDataPoint,
    APCreate,
    APUpdate,
)


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

    async def get_all_aps(self) -> List[Dict[str, Any]]:
        """Obtiene todos los APs con sus últimas estadísticas."""
        from sqlmodel import select
        from ..models.zona import Zona
        
        # 1. Fetch APs with zona_nombre via LEFT JOIN
        statement = (
            select(AP, Zona.nombre.label("zona_nombre"))
            .outerjoin(Zona, AP.zona_id == Zona.id)
        )
        result = await self.session.execute(statement)
        rows = result.all()
        
        # 2. Fetch stats
        stats_map = self._fetch_latest_stats_map()
        
        results = []
        for ap, zona_nombre in rows:
            ap_dict = ap.model_dump()
            
            # Merge stats
            stat = stats_map.get(ap.host, {})
            ap_dict.update(stat)
            
            # Add zona_nombre
            ap_dict["zona_nombre"] = zona_nombre
            
            results.append(ap_dict)
            
        return results

    def _fetch_latest_stats_map(self) -> Dict[str, Dict[str, Any]]:
        """Helper to fetch latest stats for all APs from stats DB."""
        # This logic is adapted from aps_db.get_all_aps_with_stats
        try:
            conn = get_stats_db_connection()
            if not conn:
                return {}
            
            query = """
                SELECT 
                    ap_host, client_count, airtime_total_usage
                FROM ap_stats_history
                WHERE (ap_host, timestamp) IN (
                    SELECT ap_host, MAX(timestamp)
                    FROM ap_stats_history
                    GROUP BY ap_host
                )
            """
            cursor = conn.execute(query)
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = dict(row) # row[0] is ap_host
            conn.close()
            return stats
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return {}

    async def get_ap_by_host(self, host: str) -> Dict[str, Any]:
        """Obtiene un AP específico por host."""
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado: {host}")
            
        ap_dict = ap.model_dump()
        ap_dict["password"] = decrypt_data(ap.password)
        
        # Fetch stats
        stats = self._fetch_latest_stats_for_host(host)
        ap_dict.update(stats)
        
        return ap_dict

    def _fetch_latest_stats_for_host(self, host: str) -> Dict[str, Any]:
        try:
            conn = get_stats_db_connection()
            if not conn:
                return {}
            
            query = """
                SELECT * FROM ap_stats_history WHERE ap_host = ? ORDER BY timestamp DESC LIMIT 1
            """
            cursor = conn.execute(query, (host,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else {}
        except Exception:
            return {}

    async def create_ap(self, ap_data: APCreate) -> Dict[str, Any]:
        """Crea un nuevo AP en la base de datos."""
        ap_dict = ap_data.model_dump()

        # Lógica de negocio: Asignar intervalo por defecto si no se proporciona
        if ap_dict.get("monitor_interval") is None:
            default_interval_str = settings_db.get_setting("default_monitor_interval")
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

    async def update_ap(self, host: str, ap_update: APUpdate) -> Dict[str, Any]:
        """Actualiza un AP existente."""
        ap = await self.session.get(AP, host)
        if not ap:
             raise APNotFoundError(f"AP no encontrado para actualizar: {host}")

        update_fields = ap_update.model_dump(exclude_unset=True)
        if not update_fields:
            raise APDataError("No se proporcionaron campos para actualizar.")

        # Lógica de negocio: No permitir cambiar contraseña si está vacía
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

    def get_cpes_for_ap(self, host: str) -> List[Dict[str, Any]]:
        """Obtiene los CPEs conectados a un AP desde el último snapshot."""
        # This still uses stats_db, so we can keep using the helper or move logic here.
        # Since it's purely stats DB, we can keep using stats_db helper or import it.
        return stats_db.get_cpes_for_ap_from_stats(host)

    async def get_live_data(self, host: str) -> APLiveDetail:
        """Obtiene datos en vivo de un AP y los formatea."""
        # Get credentials from DB (using SQLModel)
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado en el inventario: {host}")
            
        password = decrypt_data(ap.password)
        
        # Get the appropriate adapter based on vendor
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
            
            # Convert DeviceStatus to APLiveDetail for backwards compatibility
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
                        # MikroTik-specific fields
                        ccq=client.ccq,
                        tx_rate=client.tx_rate,
                        rx_rate=client.rx_rate,
                    )
                )
            
            # Prepare extra data with calculated fields
            extra_data = dict(status.extra) if status.extra else {}
            
            # Calculate memory usage percentage for MikroTik
            if extra_data.get("free_memory") and extra_data.get("total_memory"):
                try:
                    free = int(extra_data["free_memory"])
                    total = int(extra_data["total_memory"])
                    if total > 0:
                        used = total - free
                        extra_data["memory_usage"] = round((used / total) * 100, 1)
                except (ValueError, TypeError):
                    pass  # Skip if conversion fails
            
            # Format uptime for display (status.uptime is in seconds)
            if status.uptime:
                uptime_secs = status.uptime
                days = uptime_secs // 86400
                hours = (uptime_secs % 86400) // 3600
                minutes = (uptime_secs % 3600) // 60
                if days > 0:
                    extra_data["uptime"] = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    extra_data["uptime"] = f"{hours}h {minutes}m"
                else:
                    extra_data["uptime"] = f"{minutes}m"
            
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
                # Include vendor info for UI differentiation
                vendor=vendor,
                # Include extra data for MikroTik (CPU, memory, uptime, platform)
                extra=extra_data if extra_data else None,
            )
        finally:
            adapter.disconnect()

    async def get_wireless_interfaces(self, host: str) -> List[Dict[str, str]]:
        """
        Obtiene las interfaces inalámbricas disponibles para un AP MikroTik.
        Incluye información de banda detectada de la frecuencia real operativa.
        """
        ap = await self.session.get(AP, host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado: {host}")
        
        vendor = ap.vendor or DeviceVendor.UBIQUITI
        if vendor != DeviceVendor.MIKROTIK:
            return []  # Solo MikroTik tiene múltiples interfaces
        
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
                        i.get("ssid") or  # Direct field from wireless.py
                        i.get("original_record", {}).get("configuration.ssid") or 
                        i.get("original_record", {}).get("ssid") or 
                        None
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
            if 'ssl' in error_msg or 'handshake' in error_msg:
                raise APUnreachableError(
                    f"Error de conexión SSL al AP {host}. "
                    f"Verifique el certificado del dispositivo. Detalle: {e}"
                )
            raise APUnreachableError(f"No se pudo conectar al AP {host}: {e}")
        finally:
            adapter.disconnect()
    


    async def get_ap_history(self, host: str, period: str = "24h") -> APHistoryResponse:
        """Obtiene datos históricos de un AP desde la DB de estadísticas."""

        # Obtenemos info básica del AP (como el hostname)
        ap_info = await self.get_ap_by_host(host)  # Reutilizamos nuestro propio método

        # Lógica de conexión a la DB de stats (movida desde la API)
        stats_conn = get_stats_db_connection()
        if not stats_conn:
            return APHistoryResponse(
                host=host, hostname=ap_info.get("hostname", host), history=[]
            )

        if period == "7d":
            start_time = datetime.utcnow() - timedelta(days=7)
        elif period == "30d":
            start_time = datetime.utcnow() - timedelta(days=30)
        else:
            start_time = datetime.utcnow() - timedelta(hours=24)

        try:
            query = "SELECT timestamp, client_count, airtime_total_usage, total_throughput_tx, total_throughput_rx FROM ap_stats_history WHERE ap_host = ? AND timestamp >= ? ORDER BY timestamp ASC;"
            cursor = stats_conn.execute(query, (host, start_time))
            rows = cursor.fetchall()

            return APHistoryResponse(
                host=host,
                hostname=ap_info.get("hostname"),
                history=[HistoryDataPoint(**dict(row)) for row in rows],
            )
        except sqlite3.Error as e:
            raise APDataError(f"Error en la base de datos de estadísticas: {e}")
        finally:
            if stats_conn:
                stats_conn.close()
