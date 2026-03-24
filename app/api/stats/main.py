import logging

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy import func, text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import require_technician, current_active_user
from ...db.engine import get_session
from ...models.ap import AP
from ...models.cpe import CPE
from ...models.router import Router
from ...models.switch import Switch
from ...models.user import User
from ...models.ticket import Ticket
from ...core.constants import CPEStatus, DeviceStatus
# Models specifically for response
from .models import (
    CPECount, SwitchCount, TopAP, TopCPE, 
    TicketStats, RouterCount, APCount,
    TopRouterConsumption, TopOfflineDevice
)
from ...services.core.settings_service import SettingsService

from ...repositories.log_repository import (
    count_event_logs,
    get_event_logs_paginated,
)

router = APIRouter()


@router.get("/stats/top-aps-by-airtime", response_model=list[TopAP])
async def get_top_aps_by_airtime(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Returns top APs by airtime usage.
    """
    try:
        # We need the latest stats for each AP.
        # Efficient way in SQLModel: Join AP with APStats on subquery?
        # Or just window function via raw SQL like stats_db, but APStats is now in same DB.
        
        # Using raw SQL for window function support is cleaner for "latest by group"
        query = text(f"""
            WITH LatestStats AS (
                SELECT 
                    ap_host, airtime_total_usage,
                    ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                FROM apstats
                WHERE airtime_total_usage IS NOT NULL
            )
            SELECT a.hostname, a.host, s.airtime_total_usage
            FROM aps as a 
            JOIN LatestStats s ON a.host = s.ap_host AND s.rn = 1
            ORDER BY s.airtime_total_usage DESC 
            LIMIT :limit;
        """)
        
        result = await session.exec(query, params={"limit": limit})
        rows = [dict(row) for row in result.mappings()]
        return rows
        
    except Exception as e:
        logger.error(f"Error getting top APs: {e}", exc_info=True)
        return []


@router.get("/stats/top-cpes-by-signal", response_model=list[TopCPE])
async def get_top_cpes_by_weak_signal(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        settings_service = SettingsService(session)
        warning_str = await settings_service.get_setting_value("cpe_signal_warning_threshold")
        warning_threshold = float(warning_str) if warning_str else -62.0

        query = text(f"""
            WITH LatestCPEStats AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                FROM cpestats
                WHERE signal IS NOT NULL
            )
            SELECT cpe_hostname, cpe_mac, ap_host, signal
            FROM LatestCPEStats
            WHERE rn = 1 AND signal <= :warning_threshold
            ORDER BY signal ASC 
            LIMIT :limit;
        """)
        
        result = await session.exec(query, params={"limit": limit, "warning_threshold": warning_threshold})
        rows = [dict(row) for row in result.mappings()]
        return rows
    except Exception as e:
        logger.error(f"Error getting top CPEs: {e}", exc_info=True)
        return []


@router.get("/stats/top-routers-by-consumption", response_model=list[TopRouterConsumption])
async def get_top_routers_by_consumption(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """
    Returns top routers by sum of wan_rx_bps + wan_tx_bps.
    Only considers routers where wan_interface is not null.
    """
    try:
        # Priority: order by total accumulated bytes (wan_rx_bytes + wan_tx_bytes)
        # Fallback to BPS if bytes are not available yet
        # Uses two separate CTEs: one for latest bytes row, one for latest BPS row
        query = text("""
            WITH LatestBytes AS (
                SELECT 
                    router_host, wan_rx_bytes, wan_tx_bytes,
                    ROW_NUMBER() OVER(PARTITION BY router_host ORDER BY timestamp DESC) as rn
                FROM routerstats
                WHERE wan_rx_bytes IS NOT NULL
            ),
            LatestBPS AS (
                SELECT 
                    router_host, wan_rx_bps, wan_tx_bps,
                    ROW_NUMBER() OVER(PARTITION BY router_host ORDER BY timestamp DESC) as rn
                FROM routerstats
                WHERE wan_rx_bps IS NOT NULL
            )
            SELECT 
                r.hostname, 
                r.host,
                COALESCE(b.wan_rx_bytes, 0) as wan_rx_bytes,
                COALESCE(b.wan_tx_bytes, 0) as wan_tx_bytes,
                COALESCE(p.wan_rx_bps, 0) as wan_rx_bps,
                COALESCE(p.wan_tx_bps, 0) as wan_tx_bps,
                (COALESCE(b.wan_rx_bytes, 0) + COALESCE(b.wan_tx_bytes, 0)) as total_bytes,
                (COALESCE(p.wan_rx_bps, 0) + COALESCE(p.wan_tx_bps, 0)) as total_bps
            FROM routers as r
            LEFT JOIN LatestBytes b ON r.host = b.router_host AND b.rn = 1
            LEFT JOIN LatestBPS p ON r.host = p.router_host AND p.rn = 1
            WHERE r.wan_interface IS NOT NULL
              AND (b.wan_rx_bytes IS NOT NULL OR p.wan_rx_bps IS NOT NULL)
            ORDER BY total_bytes DESC, total_bps DESC
            LIMIT :limit;
        """)
        
        result = await session.exec(query, params={"limit": limit})
        rows = [dict(row) for row in result.mappings()]
        return rows
        
    except Exception as e:
        logger.error(f"Error getting top routers by consumption: {e}", exc_info=True)
        return []


@router.get("/stats/top-offline-devices", response_model=list[TopOfflineDevice])
async def get_top_offline_devices(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """
    Returns top recently offline devices (routers, switches, aps) combined.
    Items are sorted by last_checked ascending (longest time offline first) or descending depending on preference.
    Here we order by last_checked DESC to show most recently dropped devices, or ASC to show oldest offline.
    """
    try:
        # We will union all queries ensuring the structure matches TopOfflineDevice
        # Device status should be strictly offline
        query = text(f"""
            SELECT hostname, host, 'Router' as device_type, last_checked
            FROM routers
            WHERE last_status = 'offline'
            
            UNION ALL
            
            SELECT hostname, host, 'AP' as device_type, last_checked
            FROM aps
            WHERE last_status = 'offline'
            
            UNION ALL
            
            SELECT hostname, host, 'Switch' as device_type, last_checked
            FROM switches
            WHERE last_status = 'offline'
            
            ORDER BY last_checked DESC
            LIMIT :limit;
        """)
        
        result = await session.exec(query, params={"limit": limit})
        rows_result = []
        for row in result.mappings():
            item = dict(row)
            if item.get("last_checked"):
                # Format datetime string safely for frontend
                try:
                    item["last_checked"] = item["last_checked"][:19].replace("T", " ")
                except:
                    item["last_checked"] = str(item["last_checked"])
            else:
                 item["last_checked"] = "Desconocido"
            rows_result.append(item)
            
        return rows_result
        
    except Exception as e:
        logger.error(f"Error getting top offline devices: {e}", exc_info=True)
        return []


@router.get("/stats/cpe-count", response_model=CPECount)
async def get_cpe_total_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        # Total Enabled
        total = await session.exec(select(func.count()).select_from(CPE).where(CPE.is_enabled == True))
        total = total.one()

        # Active
        active = await session.exec(select(func.count()).select_from(CPE).where(CPE.status == CPEStatus.ACTIVE, CPE.is_enabled == True))
        active = active.one()

        # Offline
        offline = await session.exec(select(func.count()).select_from(CPE).where(CPE.status == CPEStatus.OFFLINE, CPE.is_enabled == True))
        offline = offline.one()

        # Disabled
        disabled = await session.exec(select(func.count()).select_from(CPE).where(CPE.is_enabled == False))
        disabled = disabled.one()

        return {
            "total_cpes": total,
            "active": active,
            "offline": offline,
            "disabled": disabled,
        }
    except Exception as e:
        logger.error(f"Error obteniendo conteo de CPEs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas de CPEs")


@router.get("/stats/switch-count", response_model=SwitchCount)
async def get_switch_total_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        total = await session.exec(select(func.count()).select_from(Switch))
        total = total.one()
        
        online = await session.exec(select(func.count()).select_from(Switch).where(Switch.last_status == DeviceStatus.ONLINE, Switch.is_enabled == True))
        online = online.one()
        
        offline = await session.exec(select(func.count()).select_from(Switch).where(Switch.last_status == DeviceStatus.OFFLINE, Switch.is_enabled == True))
        offline = offline.one()

        return {
            "total_switches": total,
            "online": online,
            "offline": offline,
        }
    except Exception as e:
        logger.error(f"Error obteniendo conteo de switches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas de switches")


@router.get("/stats/router-count", response_model=RouterCount)
async def get_router_total_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        total = await session.exec(select(func.count()).select_from(Router))
        total = total.one()
        
        online = await session.exec(select(func.count()).select_from(Router).where(Router.last_status == DeviceStatus.ONLINE, Router.is_enabled == True))
        online = online.one()
        
        offline = await session.exec(select(func.count()).select_from(Router).where(Router.last_status == DeviceStatus.OFFLINE, Router.is_enabled == True))
        offline = offline.one()

        return {
            "total_routers": total,
            "online": online,
            "offline": offline,
        }
    except Exception as e:
        logger.error(f"Error obteniendo conteo de routers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas de routers")


@router.get("/stats/ap-count", response_model=APCount)
async def get_ap_total_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        total = await session.exec(select(func.count()).select_from(AP))
        total = total.one()
        
        online = await session.exec(select(func.count()).select_from(AP).where(AP.last_status == DeviceStatus.ONLINE, AP.is_enabled == True))
        online = online.one()
        
        offline = await session.exec(select(func.count()).select_from(AP).where(AP.last_status == DeviceStatus.OFFLINE, AP.is_enabled == True))
        offline = offline.one()

        return {
            "total_aps": total,
            "online": online,
            "offline": offline,
        }
    except Exception as e:
        logger.error(f"Error obteniendo conteo de aps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas de aps")


@router.get("/stats/tickets", response_model=TicketStats)
async def get_ticket_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        # Total
        total = await session.exec(select(func.count()).select_from(Ticket))
        total = total.one()

        # By Status
        open_t = await session.exec(select(func.count()).select_from(Ticket).where(Ticket.status == "open"))
        resolved_t = await session.exec(select(func.count()).select_from(Ticket).where(Ticket.status == "resolved"))
        pending_t = await session.exec(select(func.count()).select_from(Ticket).where(Ticket.status == "pending"))

        # By Type (assuming default 'support' if null, but model has default)
        support = await session.exec(select(func.count()).select_from(Ticket).where(Ticket.ticket_type == "support"))
        installation = await session.exec(select(func.count()).select_from(Ticket).where(Ticket.ticket_type == "installation"))

        return {
            "total_tickets": total,
            "open_tickets": open_t.one(),
            "resolved_tickets": resolved_t.one(),
            "pending_tickets": pending_t.one(),
            "support_tickets": support.one(),
            "installation_tickets": installation.one(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error obteniendo estadísticas de tickets")


@router.get("/stats/events")
async def get_dashboard_events(
    host: str = None,
    page: int = 1,
    page_size: int = 10,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """
    Obtiene los logs paginados.
    """
    logs = await get_event_logs_paginated(session, host, page, page_size)
    total_records = await count_event_logs(session, host)

    total_pages = (total_records + page_size - 1) // page_size

    return {
        "items": logs,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
