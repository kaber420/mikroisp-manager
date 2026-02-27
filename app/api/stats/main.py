import logging

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy import func, text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...core.users import current_active_user
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
    TicketStats, RouterCount, APCount
)

from ...repositories.log_repository import (
    count_event_logs,
    get_event_logs_paginated,
)

router = APIRouter()


@router.get("/stats/top-aps-by-airtime", response_model=list[TopAP])
async def get_top_aps_by_airtime(
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
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
            WHERE rn = 1
            ORDER BY signal ASC 
            LIMIT :limit;
        """)
        
        result = await session.exec(query, params={"limit": limit})
        rows = [dict(row) for row in result.mappings()]
        return rows
    except Exception as e:
        logger.error(f"Error getting top CPEs: {e}", exc_info=True)
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
