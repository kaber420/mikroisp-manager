
import logging
import os
from datetime import datetime
from typing import Any, Sequence

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, text

from ..core.constants import DeviceStatus
from ..models.ap import AP
from ..models.zona import Zona
from ..utils.security import decrypt_data, encrypt_data
from .base import get_stats_db_file


async def get_enabled_aps_for_monitor(session: AsyncSession) -> Sequence[AP]:
    """
    Obtiene la lista de APs activos desde la BD y descifra sus contraseñas.
    Includes vendor and api_port for multi-vendor adapter support.
    """
    try:
        stmt = select(AP).where(AP.is_enabled == True)
        result = await session.exec(stmt)
        aps = result.all()

        output = []
        for ap in aps:
            ap_out = ap.model_copy()
            if ap_out.password:
                try:
                    ap_out.password = decrypt_data(ap_out.password)
                except Exception:
                    pass
            
            # Default vendor to ubiquiti for backwards compatibility
            if not ap_out.vendor:
                ap_out.vendor = "ubiquiti"
            
            output.append(ap_out)
        return output
    except Exception as e:
        logging.error(f"No se pudo obtener la lista de APs de la base de datos: {e}")
        return []


async def get_ap_status(session: AsyncSession, host: str) -> str | None:
    """Obtiene el último estado conocido de un AP."""
    try:
        ap = await session.get(AP, host)
        return ap.last_status if ap else None
    except Exception:
        return None


async def update_ap_status(session: AsyncSession, host: str, status: str, data: dict[str, Any] | None = None):
    """Actualiza el estado de un AP, y opcionalmente sus metadatos si está online."""
    try:
        now = datetime.utcnow()
        # We can use update_ap_in_db logic or raw update for speed/simplicity
        # Logic is complex for "data" parsing.
        
        updates = {"last_status": status, "last_checked": now}
        
        if status == DeviceStatus.ONLINE and data:
            if "host" in data and isinstance(data.get("host"), dict):
                # Legacy Ubiquiti format
                host_info = data.get("host", {})
                interfaces = data.get("interfaces", [{}, {}])
                updates["mac"] = interfaces[1].get("hwaddr") if len(interfaces) > 1 else None
                updates["hostname"] = host_info.get("hostname")
                updates["model"] = host_info.get("devmodel")
                updates["firmware"] = host_info.get("fwversion")
            else:
                updates["mac"] = data.get("mac")
                updates["hostname"] = data.get("hostname")
                updates["model"] = data.get("model")
                updates["firmware"] = data.get("firmware")
                
            updates["last_seen"] = now

        # Use efficient update
        stmt = select(AP).where(AP.host == host)
        result = await session.exec(stmt)
        ap = result.one_or_none()
        if ap:
            for k, v in updates.items():
                setattr(ap, k, v)
            session.add(ap)
            await session.commit()
            
    except Exception as e:
        logging.error(f"Error updating AP status {host}: {e}")


async def get_ap_credentials(session: AsyncSession, host: str) -> dict[str, Any] | None:
    """Obtiene el usuario y la contraseña de un AP para la conexión en vivo."""
    try:
        ap = await session.get(AP, host)
        if not ap:
            return None
        
        creds = {"username": ap.username, "password": ap.password}
        if creds["password"]:
            try:
                creds["password"] = decrypt_data(creds["password"])
            except Exception:
                pass
        return creds
    except Exception:
        return None


async def create_ap_in_db(session: AsyncSession, ap_data: dict[str, Any]) -> dict[str, Any]:
    """Inserta un nuevo AP en la base de datos."""
    # Prepare data
    data = ap_data.copy()
    if "password" in data:
        data["password"] = encrypt_data(data["password"])
    
    # Set default first_seen if not provided
    if "first_seen" not in data:
        data["first_seen"] = datetime.utcnow()

    ap = AP(**data)
    session.add(ap)
    try:
        await session.commit()
        await session.refresh(ap)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Host duplicado o zona_id inválida. Error: {e}")

    # Return fetched version with stats (likely empty stats but standard return)
    return await get_ap_by_host_with_stats(session, ap.host)


async def get_all_aps_with_stats(session: AsyncSession) -> list[dict[str, Any]]:
    """Obtiene todos los APs, uniendo los datos de estado más recientes de la DB de estadísticas."""
    stats_db_file = get_stats_db_file()
    attached = False
    
    try:
        if os.path.exists(stats_db_file):
            try:
                # Attempt to attach
                await session.execute(text(f"ATTACH DATABASE '{stats_db_file}' AS stats_db"))
                attached = True
                
                query = """
                    WITH LatestStats AS (
                        SELECT 
                            ap_host, client_count, airtime_total_usage,
                            ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                        FROM stats_db.ap_stats_history
                    )
                    SELECT a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage
                    FROM aps AS a
                    LEFT JOIN zonas AS z ON a.zona_id = z.id
                    LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
                    ORDER BY a.host;
                """
                result = await session.execute(text(query))
                rows = result.mappings().all()
                return [dict(row) for row in rows]
            except Exception:
                # Fallback if attach fails or stats_db locked/issue
                pass
                
    finally:
        if attached:
            try:
                await session.execute(text("DETACH DATABASE stats_db"))
            except Exception:
                pass

    # Fallback logic (SQLModel)
    stmt = select(AP, Zona.nombre.label("zona_nombre")).outerjoin(Zona, AP.zona_id == Zona.id).order_by(AP.host)
    result_obj = await session.exec(stmt)
    
    output = []
    for ap, zona_name in result_obj.all():
        d = ap.model_dump()
        d['zona_nombre'] = zona_name
        d['client_count'] = None
        d['airtime_total_usage'] = None
        output.append(d)
    return output


async def get_ap_by_host_with_stats(session: AsyncSession, host: str) -> dict[str, Any] | None:
    """Obtiene un AP específico, uniendo sus datos de estado más recientes."""
    stats_db_file = get_stats_db_file()
    attached = False
    
    try:
        if os.path.exists(stats_db_file):
            try:
                await session.execute(text(f"ATTACH DATABASE '{stats_db_file}' AS stats_db"))
                attached = True
                query = """
                    WITH LatestStats AS (
                        SELECT *, ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                        FROM stats_db.ap_stats_history
                        WHERE ap_host = :host
                    )
                    SELECT 
                        a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage, s.airtime_tx_usage, 
                        s.airtime_rx_usage, s.total_throughput_tx, s.total_throughput_rx, s.noise_floor, s.chanbw, 
                        s.frequency, s.essid, s.total_tx_bytes, s.total_rx_bytes, s.gps_lat, s.gps_lon, s.gps_sats
                    FROM aps AS a
                    LEFT JOIN zonas AS z ON a.zona_id = z.id
                    LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
                    WHERE a.host = :host;
                """
                result = await session.execute(text(query), {"host": host})
                row = result.mappings().one_or_none()
                return dict(row) if row else None
            except Exception:
                pass # Fall through to fallback logic below
        
        # SQLModel fallback
        stmt = select(AP, Zona.nombre.label("zona_nombre")).outerjoin(Zona, AP.zona_id == Zona.id).where(AP.host == host)
        result_obj = await session.exec(stmt)
        res = result_obj.first()
        if not res:
             return None
             
        ap, zona_name = res
        d = ap.model_dump()
        d['zona_nombre'] = zona_name
        return d
        
    finally:
        if attached:
            try:
                await session.execute(text("DETACH DATABASE stats_db"))
            except Exception:
                pass


async def update_ap_in_db(session: AsyncSession, host: str, updates: dict[str, Any]) -> int:
    """Actualiza un AP en la base de datos y devuelve el número de filas afectadas."""
    if not updates:
        return 0

    try:
        ap = await session.get(AP, host)
        if not ap:
            return 0

        clean_updates = updates.copy()
        if "password" in clean_updates and clean_updates["password"]:
            clean_updates["password"] = encrypt_data(clean_updates["password"])

        for k, v in clean_updates.items():
            if hasattr(ap, k):
                setattr(ap, k, v)
        
        session.add(ap)
        await session.commit()
        return 1
    except Exception as e:
        # logging.error(f"Error updating AP {host}: {e}")
        await session.rollback()
        return 0


async def delete_ap_from_db(session: AsyncSession, host: str) -> int:
    """Elimina un AP de la base de datos y devuelve el número de filas afectadas."""
    try:
        ap = await session.get(AP, host)
        if not ap:
            return 0
        await session.delete(ap)
        await session.commit()
        return 1
    except Exception:
        await session.rollback()
        return 0
