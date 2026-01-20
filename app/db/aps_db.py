# app/db/aps_db.py
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

from ..core.constants import DeviceStatus
from ..utils.security import decrypt_data, encrypt_data
from .base import get_db_connection, get_stats_db_file


def get_enabled_aps_for_monitor() -> list:
    """
    Obtiene la lista de APs activos desde la BD y descifra sus contraseñas.
    Includes vendor and api_port for multi-vendor adapter support.
    """
    aps_to_monitor = []
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT host, username, password, vendor, api_port FROM aps WHERE is_enabled = TRUE"
        )

        for row in cursor.fetchall():
            creds = dict(row)
            creds["password"] = decrypt_data(creds["password"])
            # Default vendor to ubiquiti for backwards compatibility
            if not creds.get("vendor"):
                creds["vendor"] = "ubiquiti"
            aps_to_monitor.append(creds)

        conn.close()
    except sqlite3.Error as e:
        logging.error(f"No se pudo obtener la lista de APs de la base de datos: {e}")
    return aps_to_monitor


def get_ap_status(host: str) -> str | None:
    """Obtiene el último estado conocido de un AP."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_status FROM aps WHERE host = ?", (host,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def update_ap_status(host: str, status: str, data: dict[str, Any] | None = None):
    """Actualiza el estado de un AP, y opcionalmente sus metadatos si está online."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()

    if status == DeviceStatus.ONLINE and data:
        if "host" in data and isinstance(data.get("host"), dict):
            # Legacy Ubiquiti format
            host_info = data.get("host", {})
            interfaces = data.get("interfaces", [{}, {}])
            mac = interfaces[1].get("hwaddr") if len(interfaces) > 1 else None
            hostname = host_info.get("hostname")
            model = host_info.get("devmodel")
            firmware = host_info.get("fwversion")
        else:
            mac = data.get("mac")
            hostname = data.get("hostname")
            model = data.get("model")
            firmware = data.get("firmware")

        cursor.execute(
            """
        UPDATE aps 
        SET mac = ?, hostname = ?, model = ?, firmware = ?, last_status = ?, last_seen = ?, last_checked = ?
        WHERE host = ?
        """,
            (
                mac,
                hostname,
                model,
                firmware,
                status,
                now,
                now,
                host,
            ),
        )
    else:  # AP está offline o no hay datos
        cursor.execute(
            "UPDATE aps SET last_status = ?, last_checked = ? WHERE host = ?",
            (status, now, host),
        )

    conn.commit()
    conn.close()


def get_ap_credentials(host: str) -> dict[str, Any] | None:
    """Obtiene el usuario y la contraseña de un AP para la conexión en vivo."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT username, password FROM aps WHERE host = ?", (host,))
    creds = cursor.fetchone()
    conn.close()

    if not creds:
        return None

    creds_dict = dict(creds)
    creds_dict["password"] = decrypt_data(creds_dict["password"])
    return creds_dict


def create_ap_in_db(ap_data: dict[str, Any]) -> dict[str, Any]:
    """Inserta un nuevo AP en la base de datos."""
    conn = get_db_connection()
    try:
        encrypted_password = encrypt_data(ap_data["password"])

        conn.execute(
            "INSERT INTO aps (host, username, password, zona_id, is_enabled, monitor_interval, first_seen) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                ap_data["host"],
                ap_data["username"],
                encrypted_password,  # <-- Usar variable cifrada
                ap_data["zona_id"],
                ap_data["is_enabled"],
                ap_data["monitor_interval"],
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Host duplicado o zona_id inválida. Error: {e}")
    finally:
        conn.close()

    new_ap = get_ap_by_host_with_stats(ap_data["host"])
    if not new_ap:
        raise ValueError("No se pudo recuperar el AP después de la creación.")
    return new_ap


def get_all_aps_with_stats() -> list[dict[str, Any]]:
    """Obtiene todos los APs, uniendo los datos de estado más recientes de la DB de estadísticas."""
    conn = get_db_connection()
    stats_db_file = get_stats_db_file()

    if os.path.exists(stats_db_file):
        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
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
        except sqlite3.OperationalError:
            query = "SELECT a.*, z.nombre as zona_nombre, NULL as client_count, NULL as airtime_total_usage FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id ORDER BY a.host;"
    else:
        query = "SELECT a.*, z.nombre as zona_nombre, NULL as client_count, NULL as airtime_total_usage FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id ORDER BY a.host;"

    cursor = conn.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_ap_by_host_with_stats(host: str) -> dict[str, Any] | None:
    """Obtiene un AP específico, uniendo sus datos de estado más recientes."""
    conn = get_db_connection()
    stats_db_file = get_stats_db_file()

    if os.path.exists(stats_db_file):
        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
            query = """
                WITH LatestStats AS (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                    FROM stats_db.ap_stats_history
                    WHERE ap_host = ?
                )
                SELECT 
                    a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage, s.airtime_tx_usage, 
                    s.airtime_rx_usage, s.total_throughput_tx, s.total_throughput_rx, s.noise_floor, s.chanbw, 
                    s.frequency, s.essid, s.total_tx_bytes, s.total_rx_bytes, s.gps_lat, s.gps_lon, s.gps_sats
                FROM aps AS a
                LEFT JOIN zonas AS z ON a.zona_id = z.id
                LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
                WHERE a.host = ?;
            """
            cursor = conn.execute(query, (host, host))
        except sqlite3.OperationalError:
            query = "SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id WHERE a.host = ?"
            cursor = conn.execute(query, (host,))
    else:
        query = "SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id WHERE a.host = ?"
        cursor = conn.execute(query, (host,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


_APS_ALLOWED_COLUMNS = frozenset(
    [
        "username",
        "password",
        "zona_id",
        "is_enabled",
        "monitor_interval",
        "mac",
        "hostname",
        "model",
        "firmware",
        "last_status",
        "last_seen",
        "last_checked",
        "vendor",
        "api_port",
    ]
)


def update_ap_in_db(host: str, updates: dict[str, Any]) -> int:
    """Actualiza un AP en la base de datos y devuelve el número de filas afectadas."""
    if not updates:
        return 0

    # Validate column names against whitelist to prevent SQL injection
    invalid_keys = set(updates.keys()) - _APS_ALLOWED_COLUMNS
    if invalid_keys:
        raise ValueError(f"Invalid column names: {invalid_keys}")

    conn = get_db_connection()

    if "password" in updates and updates["password"]:
        updates["password"] = encrypt_data(updates["password"])

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])  # nosec B608
    values = list(updates.values())
    values.append(host)

    cursor = conn.execute(f"UPDATE aps SET {set_clause} WHERE host = ?", tuple(values))  # nosec B608
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount


def delete_ap_from_db(host: str) -> int:
    """Elimina un AP de la base de datos y devuelve el número de filas afectadas."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM aps WHERE host = ?", (host,))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount
