# app/services/ap_service.py
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Importaciones de nuestras utilidades y capas de DB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from ..models.ap import AP
from ..utils.security import encrypt_data, decrypt_data
from ..utils.device_clients.client_provider import get_ubiquiti_client
from ..db import settings_db, stats_db
from ..db.base import get_stats_db_connection

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

        client = get_ubiquiti_client(
            host=host,
            username=ap.username,
            password=password,
            port=443, # Default port, or add to model if needed. Model doesn't have port currently.
            http_mode=False, # Default
        )
        status_data = client.get_status_data()

        if not status_data:
            raise APUnreachableError(
                f"No se pudo obtener datos del AP {host}. Puede estar offline."
            )

        # --- INICIO DE LÓGICA DE TRANSFORMACIÓN (movida desde la API) ---
        host_info = status_data.get("host", {})
        wireless_info = status_data.get("wireless", {})
        ath0_status = status_data.get("interfaces", [{}, {}])[1].get("status", {})
        gps_info = status_data.get("gps", {})
        throughput_info = wireless_info.get("throughput", {})
        polling_info = wireless_info.get("polling", {})

        clients_list = []
        for cpe_data in wireless_info.get("sta", []):
            remote = cpe_data.get("remote", {})
            stats_data = cpe_data.get("stats", {})
            airmax = cpe_data.get("airmax", {})
            eth_info = remote.get("ethlist", [{}])[0]
            chainrssi = cpe_data.get("chainrssi", [None, None, None])

            clients_list.append(
                CPEDetail(
                    cpe_mac=cpe_data.get("mac"),
                    cpe_hostname=remote.get("hostname"),
                    ip_address=cpe_data.get("lastip"),
                    signal=cpe_data.get("signal"),
                    signal_chain0=chainrssi[0],
                    signal_chain1=chainrssi[1],
                    noisefloor=cpe_data.get("noisefloor"),
                    dl_capacity=airmax.get("dl_capacity"),
                    ul_capacity=airmax.get("ul_capacity"),
                    throughput_rx_kbps=remote.get("rx_throughput"),
                    throughput_tx_kbps=remote.get("tx_throughput"),
                    total_rx_bytes=stats_data.get("rx_bytes"),
                    total_tx_bytes=stats_data.get("tx_bytes"),
                    cpe_uptime=remote.get("uptime"),
                    eth_plugged=eth_info.get("plugged"),
                    eth_speed=eth_info.get("speed"),
                )
            )

        return APLiveDetail(
            host=host,
            username=ap.username,
            is_enabled=True,  # Asumimos True si logramos conectar
            hostname=host_info.get("hostname"),
            model=host_info.get("devmodel"),
            mac=status_data.get("interfaces", [{}, {}])[1].get("hwaddr"),
            firmware=host_info.get("fwversion"),
            last_status="online",
            client_count=wireless_info.get("count"),
            noise_floor=wireless_info.get("noisef"),
            chanbw=wireless_info.get("chanbw"),
            frequency=wireless_info.get("frequency"),
            essid=wireless_info.get("essid"),
            total_tx_bytes=ath0_status.get("tx_bytes"),
            total_rx_bytes=ath0_status.get("rx_bytes"),
            gps_lat=gps_info.get("lat"),
            gps_lon=gps_info.get("lon"),
            gps_sats=gps_info.get("sats"),
            total_throughput_tx=throughput_info.get("tx"),
            total_throughput_rx=throughput_info.get("rx"),
            airtime_total_usage=polling_info.get("use"),
            airtime_tx_usage=polling_info.get("tx_use"),
            airtime_rx_usage=polling_info.get("rx_use"),
            clients=clients_list,
        )
        # --- FIN DE LÓGICA DE TRANSFORMACIÓN ---

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
