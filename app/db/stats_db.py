# app/db/stats_db.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import get_db_connection, get_stats_db_connection
from .init_db import _setup_stats_db  # Usamos la función de configuración


def save_router_monitor_stats(router_host: str, stats: Dict[str, Any]) -> bool:
    """
    Guarda las estadísticas de un router en la tabla de historial.
    Retorna True si se guardó exitosamente, False en caso de error.
    
    Expected stats format from fetch_router_stats():
    {
        "cpu_load": 5,
        "free_memory": 100000,
        "total_memory": 200000,
        "uptime": "1w2d",
        "version": "7.x",
        "board_name": "RB4011",
        "total_disk": 16777216,
        "free_disk": 8388608,
        "voltage": 24.5,
        "temperature": 35,
        ...
    }
    """
    _setup_stats_db()
    
    conn = get_stats_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    
    try:
        # Direct mapping from flat stats dict (from fetch_router_stats)
        cursor.execute(
            """
            INSERT INTO router_stats_history (
                timestamp, router_host, cpu_load, free_memory, total_memory,
                free_hdd, total_hdd, voltage, temperature, uptime,
                board_name, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                router_host,
                stats.get("cpu_load"),
                stats.get("free_memory"),
                stats.get("total_memory"),
                stats.get("free_disk"),  # Renamed from free_hdd
                stats.get("total_disk"),  # Renamed from total_hdd
                stats.get("voltage"),
                stats.get("temperature"),
                stats.get("uptime"),
                stats.get("board_name"),
                stats.get("version"),
            ),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error guardando stats de router {router_host}: {e}")
        return False
    finally:
        conn.close()


def get_router_monitor_stats_history(
    router_host: str, range_hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Retrieves historical stats for a router from the stats database.
    
    Args:
        router_host: The router IP/hostname.
        range_hours: How many hours of history to fetch (default 24).
    
    Returns:
        A list of dicts with timestamp and stats.
    """
    conn = get_stats_db_connection()
    if not conn:
        return []
    
    try:
        query = """
            SELECT 
                timestamp, cpu_load, free_memory, total_memory,
                free_hdd, total_hdd, voltage, temperature, uptime,
                board_name, version
            FROM router_stats_history
            WHERE router_host = ?
              AND timestamp >= datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        """
        cursor = conn.execute(query, (router_host, range_hours))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except Exception as e:
        print(f"Error fetching router history for {router_host}: {e}")
        return []
    finally:
        conn.close()


def save_device_stats(ap_host: str, status: "DeviceStatus", vendor: str = "ubiquiti"):
    """
    Saves device status from adapters to the stats database.
    This is a vendor-agnostic function that works with DeviceStatus objects.
    
    Args:
        ap_host: The AP host/IP
        status: DeviceStatus object from adapter
        vendor: Vendor name ('ubiquiti', 'mikrotik', etc.)
    """
    from ..utils.device_clients.adapters.base import DeviceStatus, ConnectedClient
    
    _setup_stats_db()
    
    conn = get_stats_db_connection()
    if not conn:
        print(f"Error: No se pudo conectar a la base de datos de estadísticas para {ap_host}.")
        return
    
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    
    try:
        # Insert AP stats
        cursor.execute(
            """
            INSERT INTO ap_stats_history (
                timestamp, ap_host, vendor, uptime, cpuload, freeram, client_count, noise_floor,
                total_throughput_tx, total_throughput_rx, airtime_total_usage, 
                airtime_tx_usage, airtime_rx_usage, frequency, chanbw, essid,
                total_tx_bytes, total_rx_bytes, gps_lat, gps_lon, gps_sats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                ap_host,
                vendor,
                status.uptime,
                status.extra.get("cpu_load"),
                status.extra.get("free_memory"),
                status.client_count,
                status.noise_floor,
                status.tx_throughput,
                status.rx_throughput,
                status.airtime_usage,
                status.extra.get("airtime_tx"),
                status.extra.get("airtime_rx"),
                status.frequency,
                status.channel_width,
                status.essid,
                status.tx_bytes,
                status.rx_bytes,
                status.gps_lat,
                status.gps_lon,
                status.extra.get("gps_sats"),
            ),
        )
        
        # Insert CPE/client stats
        for client in status.clients:
            cursor.execute(
                """
                INSERT INTO cpe_stats_history (
                    timestamp, ap_host, vendor, cpe_mac, cpe_hostname, ip_address, signal, 
                    signal_chain0, signal_chain1, noisefloor, cpe_tx_power, distance, 
                    dl_capacity, ul_capacity, airmax_cinr_rx, airmax_usage_rx, 
                    airmax_cinr_tx, airmax_usage_tx, throughput_rx_kbps, throughput_tx_kbps, 
                    total_rx_bytes, total_tx_bytes, cpe_uptime, ccq, tx_rate, rx_rate,
                    ssid, band
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    ap_host,
                    vendor,
                    client.mac,
                    client.hostname,
                    client.ip_address,
                    client.signal,
                    client.signal_chain0,
                    client.signal_chain1,
                    client.noisefloor,
                    client.extra.get("tx_power"),
                    client.extra.get("distance"),
                    client.extra.get("dl_capacity"),
                    client.extra.get("ul_capacity"),
                    client.extra.get("airmax_cinr_rx"),
                    client.extra.get("airmax_usage_rx"),
                    client.extra.get("airmax_cinr_tx"),
                    client.extra.get("airmax_usage_tx"),
                    client.rx_throughput_kbps,
                    client.tx_throughput_kbps,
                    client.rx_bytes,
                    client.tx_bytes,
                    client.uptime,
                    client.ccq,
                    client.tx_rate,
                    client.rx_rate,
                    client.ssid,
                    client.band,
                ),
            )
        
        conn.commit()
        print(f"Datos de '{status.hostname or ap_host}' guardados en la base de datos de estadísticas.")
        
    except sqlite3.Error as e:
        print(f"Error de base de datos al guardar stats para {ap_host}: {e}")
    finally:
        if conn:
            conn.close()
    
    # Also update the CPE inventory table (main inventory DB)
    _update_cpe_inventory_from_status(status)



def _update_cpe_inventory_from_status(status: "DeviceStatus"):
    """
    Updates the CPE inventory table from a DeviceStatus object.
    Works with any vendor (Ubiquiti, MikroTik, etc.)
    Sets status to 'active' for seen CPEs.
    """
    from ..utils.device_clients.adapters.base import DeviceStatus
    
    if not status.clients:
        # Still run stale check even if no clients seen
        _mark_stale_cpes_offline()
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    
    try:
        for client in status.clients:
            cursor.execute(
                """
                INSERT INTO cpes (mac, hostname, model, firmware, ip_address, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                ON CONFLICT(mac) DO UPDATE SET
                    hostname = COALESCE(excluded.hostname, hostname),
                    model = COALESCE(excluded.model, model),
                    firmware = COALESCE(excluded.firmware, firmware),
                    ip_address = COALESCE(excluded.ip_address, ip_address),
                    last_seen = excluded.last_seen,
                    status = 'active'
                """,
                (
                    client.mac,
                    client.hostname,
                    client.extra.get("model") or client.extra.get("platform"),
                    client.extra.get("firmware") or client.extra.get("version"),
                    client.ip_address,
                    now,
                    now,
                ),
            )
        conn.commit()
    except Exception as e:
        print(f"Error updating CPE inventory: {e}")
    finally:
        conn.close()
    
    # Mark stale CPEs as offline
    _mark_stale_cpes_offline()


def _update_cpe_inventory(data: dict):
    """Actualiza la tabla de inventario de CPEs (dispositivos) en la DB de inventario.
    Sets status to 'active' for seen CPEs.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()

    for cpe in data.get("wireless", {}).get("sta", []):
        remote = cpe.get("remote", {})
        cursor.execute(
            """
        INSERT INTO cpes (mac, hostname, model, firmware, ip_address, first_seen, last_seen, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ON CONFLICT(mac) DO UPDATE SET
            hostname = excluded.hostname, model = excluded.model,
            firmware = excluded.firmware, ip_address = excluded.ip_address,
            last_seen = excluded.last_seen,
            status = 'active'
        """,
            (
                cpe.get("mac"),
                remote.get("hostname"),
                remote.get("platform"),
                cpe.get("version"),
                cpe.get("lastip"),
                now,
                now,
            ),
        )
    conn.commit()
    conn.close()
    
    # Mark stale CPEs as offline
    _mark_stale_cpes_offline()


def _mark_stale_cpes_offline():
    """
    Marks CPEs as 'offline' if they haven't been seen for (monitor_interval * cpe_stale_cycles) seconds.
    Only affects CPEs with status='active' and is_enabled=True.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get settings
        cursor.execute("SELECT value FROM settings WHERE key = 'default_monitor_interval'")
        row = cursor.fetchone()
        monitor_interval = int(row['value']) if row else 300
        
        cursor.execute("SELECT value FROM settings WHERE key = 'cpe_stale_cycles'")
        row = cursor.fetchone()
        stale_cycles = int(row['value']) if row else 3
        
        # Calculate threshold in seconds
        threshold_seconds = monitor_interval * stale_cycles
        
        # Mark stale CPEs as offline
        cursor.execute(
            """
            UPDATE cpes 
            SET status = 'offline'
            WHERE status = 'active' 
              AND is_enabled = 1
              AND last_seen < datetime('now', '-' || ? || ' seconds')
            """,
            (threshold_seconds,)
        )
        
        affected = cursor.rowcount
        if affected > 0:
            print(f"Marcados {affected} CPEs como offline (no vistos en {threshold_seconds}s).")
        
        conn.commit()
    except Exception as e:
        print(f"Error marking stale CPEs offline: {e}")
    finally:
        conn.close()


def save_full_snapshot(ap_host: str, data: dict):
    """
    Función central que guarda un snapshot completo de datos en la DB de estadísticas.
    """
    if not data:
        return

    _update_cpe_inventory(data)
    _setup_stats_db()

    conn = get_stats_db_connection()
    if not conn:
        print(
            f"Error: No se pudo conectar a la base de datos de estadísticas para {ap_host}."
        )
        return

    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    ap_hostname = data.get("host", {}).get("hostname", ap_host)

    wireless_info = data.get("wireless", {})
    throughput_info = wireless_info.get("throughput", {})
    polling_info = wireless_info.get("polling", {})
    ath0_status = data.get("interfaces", [{}, {}])[1].get("status", {})
    gps_info = data.get("gps", {})

    try:
        cursor.execute(
            """
            INSERT INTO ap_stats_history (
                timestamp, ap_host, uptime, cpuload, freeram, client_count, noise_floor,
                total_throughput_tx, total_throughput_rx, airtime_total_usage, 
                airtime_tx_usage, airtime_rx_usage, frequency, chanbw, essid,
                total_tx_bytes, total_rx_bytes, gps_lat, gps_lon, gps_sats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                ap_host,
                data.get("host", {}).get("uptime"),
                data.get("host", {}).get("cpuload"),
                data.get("host", {}).get("freeram"),
                wireless_info.get("count"),
                wireless_info.get("noisef"),
                throughput_info.get("tx"),
                throughput_info.get("rx"),
                polling_info.get("use"),
                polling_info.get("tx_use"),
                polling_info.get("rx_use"),
                wireless_info.get("frequency"),
                wireless_info.get("chanbw"),
                wireless_info.get("essid"),
                ath0_status.get("tx_bytes"),
                ath0_status.get("rx_bytes"),
                gps_info.get("lat"),
                gps_info.get("lon"),
                gps_info.get("sats"),
            ),
        )

        for cpe in wireless_info.get("sta", []):
            remote = cpe.get("remote", {})
            stats = cpe.get("stats", {})
            airmax = cpe.get("airmax", {})
            eth_info = remote.get("ethlist", [{}])[0]
            chainrssi = cpe.get("chainrssi", [None, None, None])

            cursor.execute(
                """
                INSERT INTO cpe_stats_history (
                    timestamp, ap_host, cpe_mac, cpe_hostname, ip_address, signal, 
                    signal_chain0, signal_chain1, noisefloor, cpe_tx_power, distance, 
                    dl_capacity, ul_capacity, airmax_cinr_rx, airmax_usage_rx, 
                    airmax_cinr_tx, airmax_usage_tx, throughput_rx_kbps, throughput_tx_kbps, 
                    total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed, eth_cable_len
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    ap_host,
                    cpe.get("mac"),
                    remote.get("hostname"),
                    cpe.get("lastip"),
                    cpe.get("signal"),
                    chainrssi[0],
                    chainrssi[1],
                    cpe.get("noisefloor"),
                    remote.get("tx_power"),
                    cpe.get("distance"),
                    airmax.get("dl_capacity"),
                    airmax.get("ul_capacity"),
                    airmax.get("rx", {}).get("cinr"),
                    airmax.get("rx", {}).get("usage"),
                    airmax.get("tx", {}).get("cinr"),
                    airmax.get("tx", {}).get("usage"),
                    remote.get("rx_throughput"),
                    remote.get("tx_throughput"),
                    stats.get("rx_bytes"),
                    stats.get("tx_bytes"),
                    remote.get("uptime"),
                    eth_info.get("plugged"),
                    eth_info.get("speed"),
                    eth_info.get("cable_len"),
                ),
            )

        for event in wireless_info.get("sta_disconnected", []):
            cursor.execute(
                """
                INSERT INTO disconnection_events (timestamp, ap_host, cpe_mac, cpe_hostname, reason_code, connection_duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    ap_host,
                    event.get("mac"),
                    event.get("hostname"),
                    event.get("reason_code"),
                    event.get("disconnect_duration"),
                ),
            )

        conn.commit()
        print(
            f"Datos de '{ap_hostname}' y sus CPEs guardados en la base de datos de estadísticas."
        )

    except sqlite3.Error as e:
        print(f"Error de base de datos al guardar snapshot para {ap_host}: {e}")
    finally:
        if conn:
            conn.close()


def get_cpes_for_ap_from_stats(host: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de CPEs más recientes para un AP específico desde la DB de estadísticas.
    Incluye el campo 'status' calculado: 'active', 'fallen', o 'disabled'.
    
    Args:
        host: AP host/IP
        status_filter: Opcional. Filtrar por status: 'active', 'fallen', 'disabled'.
    """
    from datetime import datetime, timedelta
    
    conn = get_stats_db_connection()
    if not conn:
        return []
    
    main_conn = get_db_connection()
    
    # Threshold: 10 minutes for "fallen" status
    threshold_minutes = 10
    threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)

    try:
        query = """
            WITH LatestCPEStats AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER(PARTITION BY cpe_mac, ap_host ORDER BY timestamp DESC) as rn
                FROM cpe_stats_history
                WHERE ap_host = ?
            )
            SELECT 
                timestamp,
                cpe_mac, cpe_hostname, ip_address, signal, signal_chain0, signal_chain1,
                noisefloor, dl_capacity, ul_capacity, throughput_rx_kbps, throughput_tx_kbps,
                total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed 
            FROM LatestCPEStats WHERE rn = 1 ORDER BY signal DESC;
        """
        cursor = conn.execute(query, (host,))
        stats_rows = [dict(row) for row in cursor.fetchall()]
        
        # Fetch is_enabled from main DB for each CPE
        cpe_macs = [r['cpe_mac'] for r in stats_rows]
        is_enabled_map = {}
        if cpe_macs:
            placeholders = ','.join('?' * len(cpe_macs))
            cpe_query = f"SELECT mac, is_enabled FROM cpes WHERE mac IN ({placeholders})"
            cpe_cursor = main_conn.execute(cpe_query, cpe_macs)
            for row in cpe_cursor.fetchall():
                is_enabled_map[row['mac']] = row['is_enabled']
        
        results = []
        for row in stats_rows:
            mac = row['cpe_mac']
            is_enabled = is_enabled_map.get(mac, True)  # Default to enabled if not found
            row['is_enabled'] = is_enabled
            
            # Calculate status
            if not is_enabled:
                row['status'] = 'disabled'
            else:
                stats_time = row.get('timestamp')
                if isinstance(stats_time, str):
                    try:
                        stats_time = datetime.fromisoformat(stats_time.replace('Z', '+00:00'))
                    except ValueError:
                        stats_time = None
                if stats_time and stats_time >= threshold_time:
                    row['status'] = 'active'
                else:
                    row['status'] = 'fallen'
            
            # Apply filter
            if status_filter is None or row['status'] == status_filter:
                results.append(row)
        
        return results
    finally:
        if conn:
            conn.close()
        if main_conn:
            main_conn.close()

