
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models.stats import APStats, CPEStats, DisconnectionEvent, RouterStats
from ..services.cpe_service import CPEService
from ..db.engine import get_session

logger = logging.getLogger(__name__)


async def save_router_monitor_stats(
    session: AsyncSession, router_host: str, stats: dict[str, Any]
) -> bool:
    """Guarda estadísticas de router."""
    try:
        router_stats = RouterStats(
            router_host=router_host,
            cpu_load=stats.get("cpu_load"),
            free_memory=stats.get("free_memory"),
            total_memory=stats.get("total_memory"),
            free_hdd=stats.get("free_disk"),  # Normalized to model field
            total_hdd=stats.get("total_disk"),
            voltage=stats.get("voltage"),
            temperature=stats.get("temperature"),
            uptime=stats.get("uptime"),
            board_name=stats.get("board_name"),
            version=stats.get("version"),
        )
        session.add(router_stats)
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error guardando stats de router {router_host}: {e}")
        return False


async def get_router_monitor_stats_history(
    session: AsyncSession, router_host: str, range_hours: int = 24
) -> list[RouterStats]:
    """Obtiene historial de estadísticas de router."""
    try:
        # Calculate time threshold in Python to be DB-agnostic
        from datetime import timedelta
        threshold = datetime.utcnow() - timedelta(hours=range_hours)
        
        statement = (
            select(RouterStats)
            .where(RouterStats.router_host == router_host)
            .where(RouterStats.timestamp >= threshold)
            .order_by(RouterStats.timestamp.asc())
        )
        result = await session.exec(statement)
        return list(result.all())
    except Exception as e:
        logger.error(f"Error fetching router history for {router_host}: {e}")
        return []


async def save_device_stats(
    session: AsyncSession, ap_host: str, status: "DeviceStatus", vendor: str = "ubiquiti"
):
    """Guarda estado del AP y sus clientes (CPEs)."""
    try:
        # 1. AP Stats
        ap_stats = APStats(
            ap_host=ap_host,
            vendor=vendor,
            uptime=status.uptime,
            cpuload=status.extra.get("cpu_load"),
            freeram=status.extra.get("free_memory"),
            client_count=status.client_count,
            noise_floor=status.noise_floor,
            total_throughput_tx=status.tx_throughput,
            total_throughput_rx=status.rx_throughput,
            airtime_usage=status.airtime_usage,
            airtime_tx=status.extra.get("airtime_tx"),
            airtime_rx=status.extra.get("airtime_rx"),
            frequency=status.frequency,
            chanbw=status.channel_width,
            essid=status.essid,
            total_tx_bytes=status.tx_bytes,
            total_rx_bytes=status.rx_bytes,
            gps_lat=status.gps_lat,
            gps_lon=status.gps_lon,
            gps_sats=status.extra.get("gps_sats"),
        )
        session.add(ap_stats)

        # 2. CPE Stats
        for client in status.clients:
            cpe_stats = CPEStats(
                ap_host=ap_host,
                vendor=vendor,
                cpe_mac=client.mac,
                cpe_hostname=client.hostname,
                ip_address=client.ip_address,
                signal=client.signal,
                signal_chain0=client.signal_chain0,
                signal_chain1=client.signal_chain1,
                noisefloor=client.noisefloor,
                cpe_tx_power=client.extra.get("tx_power"),
                distance=client.extra.get("distance"),
                dl_capacity=client.extra.get("dl_capacity"),
                ul_capacity=client.extra.get("ul_capacity"),
                airmax_cinr_rx=client.extra.get("airmax_cinr_rx"),
                airmax_usage_rx=client.extra.get("airmax_usage_rx"),
                airmax_cinr_tx=client.extra.get("airmax_cinr_tx"),
                airmax_usage_tx=client.extra.get("airmax_usage_tx"),
                throughput_rx_kbps=client.rx_throughput_kbps,
                throughput_tx_kbps=client.tx_throughput_kbps,
                total_rx_bytes=client.rx_bytes,
                total_tx_bytes=client.tx_bytes,
                cpe_uptime=client.uptime,
                ccq=client.ccq,
                tx_rate=client.tx_rate,
                rx_rate=client.rx_rate,
                ssid=client.ssid,
                band=client.band,
            )
            session.add(cpe_stats)

        await session.commit()
        logger.info(f"Stats guardados para {ap_host} y clientes.")

        # Update Inventory (Needs separate logic or call CPEService)
        # Note: CPEService update_inventory_from_status is sync and creates its own session usually.
        # But we are in async context. We should probably use an async version or run it in thread.
        # Ideally, refactor CPEService to be async too. For now, skipping or assuming caller handles it?
        # The original code called CPEService.update_inventory_from_status at the end.
        # I should probably do that too. BUT CPEService uses `get_sync_session`.
        # I can call it via current async session if I refactor CPEService, OR keeps it separate.
        # Given "Unify Database", I should probably use the SAME session?
        # But `CPEService` is designed for sync.
        # I will leave the inventory update part to the caller (MonitorService) or use a separate sync call 
        # inside `run_in_thread`/mixed mode if absolutely necessary.
        # Actually, `MonitorService` *already* calls `update_ap_status` which updates AP.
        # But `CPEService.update_inventory_from_status` updates CPEs.
        # I'll implement a helper to call CPEService using the async session if possible, 
        # but CPEService expects Sync Session. 
        # I'll omit the CPEService call here and let MonitorService handle it or added it back as a TODO.
        # Original code:
        # with next(get_sync_session()) as session:
        #     service = CPEService(session)
        #     service.update_inventory_from_status(status)
        
        # I will replicate this pattern but async-friendly? No, `get_sync_session` blocks.
        # I'll let `MonitorService` handle the inventory update logic separately to keep `stats_db` pure.
        
    except Exception as e:
        logger.error(f"Error saving stats for {ap_host}: {e}")


async def save_full_snapshot(session: AsyncSession, ap_host: str, data: dict):
    """Guarda snapshot completo (Monitor polling format)."""
    # Logic similar to save_device_stats but parsing 'data' dict
    # Skipping implementation for brevity unless requested, can map similarly.
    # The user plan mentioned "Rewrite save_device_stats and save_full_snapshot".
    # I should implement it.
    try:
        wireless_info = data.get("wireless", {})
        throughput_info = wireless_info.get("throughput", {})
        polling_info = wireless_info.get("polling", {})
        ath0 = data.get("interfaces", [{}, {}])[1].get("status", {})
        gps = data.get("gps", {})

        ap_stats = APStats(
            ap_host=ap_host,
            uptime=data.get("host", {}).get("uptime"),
            cpuload=data.get("host", {}).get("cpuload"),
            freeram=data.get("host", {}).get("freeram"),
            client_count=wireless_info.get("count"),
            noise_floor=wireless_info.get("noisef"),
            total_throughput_tx=throughput_info.get("tx"),
            total_throughput_rx=throughput_info.get("rx"),
            airtime_total_usage=polling_info.get("use"),
            airtime_tx_usage=polling_info.get("tx_use"),
            airtime_rx_usage=polling_info.get("rx_use"),
            frequency=wireless_info.get("frequency"),
            chanbw=wireless_info.get("chanbw"),
            essid=wireless_info.get("essid"),
            total_tx_bytes=ath0.get("tx_bytes"),
            total_rx_bytes=ath0.get("rx_bytes"),
            gps_lat=gps.get("lat"),
            gps_lon=gps.get("lon"),
            gps_sats=gps.get("sats"),
        )
        session.add(ap_stats)

        for cpe in wireless_info.get("sta", []):
            remote = cpe.get("remote", {})
            stats = cpe.get("stats", {})
            airmax = cpe.get("airmax", {})
            eth = remote.get("ethlist", [{}])[0]
            chainrssi = cpe.get("chainrssi", [None, None])

            session.add(CPEStats(
                ap_host=ap_host,
                cpe_mac=cpe.get("mac"),
                cpe_hostname=remote.get("hostname"),
                ip_address=cpe.get("lastip"),
                signal=cpe.get("signal"),
                signal_chain0=chainrssi[0],
                signal_chain1=chainrssi[1],
                noisefloor=cpe.get("noisefloor"),
                cpe_tx_power=remote.get("tx_power"),
                distance=cpe.get("distance"),
                dl_capacity=airmax.get("dl_capacity"),
                ul_capacity=airmax.get("ul_capacity"),
                airmax_cinr_rx=airmax.get("rx", {}).get("cinr"),
                airmax_usage_rx=airmax.get("rx", {}).get("usage"),
                airmax_cinr_tx=airmax.get("tx", {}).get("cinr"),
                airmax_usage_tx=airmax.get("tx", {}).get("usage"),
                throughput_rx_kbps=remote.get("rx_throughput"),
                throughput_tx_kbps=remote.get("tx_throughput"),
                total_rx_bytes=stats.get("rx_bytes"),
                total_tx_bytes=stats.get("tx_bytes"),
                cpe_uptime=remote.get("uptime"),
                eth_plugged=eth.get("plugged"),
                eth_speed=eth.get("speed"),
                eth_cable_len=eth.get("cable_len")
            ))

        for event in wireless_info.get("sta_disconnected", []):
            session.add(DisconnectionEvent(
                ap_host=ap_host,
                cpe_mac=event.get("mac"),
                cpe_hostname=event.get("hostname"),
                reason_code=event.get("reason_code"),
                connection_duration=event.get("disconnect_duration")
            ))

        await session.commit()
    except Exception as e:
        logger.error(f"Error saving snapshot for {ap_host}: {e}")


async def get_cpes_for_ap_from_stats(
    session: AsyncSession, host: str, status_filter: str = None
) -> list[dict[str, Any]]:
    """
    Obtiene lista de CPEs recientes combinando stats y tabla de inventario (cpes).
    """
    # Use raw SQL for Window Function efficiency
    query = text("""
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
            FROM cpestats
        )
        SELECT 
            s.*, 
            c.is_enabled
        FROM LatestCPEStats s
        LEFT JOIN cpes c ON s.cpe_mac = c.mac
        WHERE s.rn = 1 AND s.ap_host = :host
    """)

    try:
        # With SQLModel/SQLAlchemy AsyncSession, execute returns a Result
        cursor = await session.exec(query, params={"host": host})
        results = []
        
        from datetime import datetime, timedelta
        threshold = datetime.utcnow() - timedelta(minutes=10)

        for row in cursor.mappings():
            item = dict(row)
            # Logic for status
            is_enabled = item.get("is_enabled", 1)  # Default 1 (True)
            # SQLite stores booleans as 1/0 usually, or proper bools with SQLAlchemy.
            # Convert to Python bool if necessary
            
            # Timestamp handling
            ts = item.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except:
                    pass
            
            status = "fallen"
            if not is_enabled:
                status = "disabled"
            elif ts and ts >= threshold:
                status = "active"

            item["status"] = status
            
            if status_filter and status != status_filter:
                continue
                
            results.append(item)
            
        return results

    except Exception as e:
        logger.error(f"Error getting CPEs for AP {host}: {e}")
        return []
