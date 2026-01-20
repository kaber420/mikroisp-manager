# app/db/switches_db.py
"""
CRUD operations for Switches table.
Follows the same patterns as router_db.py.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any

from ..core.constants import DeviceStatus
from ..utils.security import decrypt_data, encrypt_data
from .base import get_db_connection

logger = logging.getLogger(__name__)


# --- Funciones CRUD para la API ---


def get_switch_by_host(host: str) -> dict[str, Any] | None:
    """Obtiene todos los datos de un switch por su host."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT rowid as id, * FROM switches WHERE host = ?", (host,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Descifrar la contraseña antes de devolverla
        data = dict(row)
        if data.get("password"):
            data["password"] = decrypt_data(data["password"])
        return data

    except sqlite3.Error as e:
        logger.error(f"Error en switches_db.get_switch_by_host para {host}: {e}")
        return None


def get_all_switches() -> list[dict[str, Any]]:
    """Obtiene todos los switches de la base de datos."""
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """SELECT host, username, zona_id, api_port, api_ssl_port, is_enabled, 
                      hostname, model, firmware, mac_address, location, notes, last_status 
               FROM switches ORDER BY host"""
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        logger.error(f"Error en switches_db.get_all_switches: {e}")
        return []


def create_switch_in_db(switch_data: dict[str, Any]) -> dict[str, Any]:
    """Inserta un nuevo switch en la base de datos."""
    conn = get_db_connection()
    try:
        # Cifrar la contraseña
        encrypted_password = encrypt_data(switch_data["password"])

        conn.execute(
            """INSERT INTO switches (host, username, password, zona_id, api_port, is_enabled, location, notes) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                switch_data["host"],
                switch_data["username"],
                encrypted_password,
                switch_data.get("zona_id"),
                switch_data.get("api_port", 8728),
                switch_data.get("is_enabled", True),
                switch_data.get("location", ""),
                switch_data.get("notes", ""),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Switch host (IP) '{switch_data['host']}' ya existe. Error: {e}")
    finally:
        conn.close()

    new_switch = get_switch_by_host(switch_data["host"])
    if not new_switch:
        raise ValueError("No se pudo recuperar el switch después de la creación.")
    return new_switch


_SWITCH_ALLOWED_COLUMNS = frozenset(
    [
        "username",
        "password",
        "zona_id",
        "api_port",
        "api_ssl_port",
        "is_enabled",
        "is_provisioned",
        "hostname",
        "model",
        "firmware",
        "mac_address",
        "location",
        "notes",
        "last_status",
        "last_checked",
    ]
)


def update_switch_in_db(host: str, updates: dict[str, Any]) -> int:
    """
    Función genérica para actualizar cualquier campo de un switch.
    Devuelve el número de filas afectadas.
    """
    if not updates:
        return 0

    # Validate column names against whitelist to prevent SQL injection
    invalid_keys = set(updates.keys()) - _SWITCH_ALLOWED_COLUMNS
    if invalid_keys:
        raise ValueError(f"Invalid column names: {invalid_keys}")

    # Cifrar la contraseña si se está actualizando
    if "password" in updates and updates["password"]:
        updates["password"] = encrypt_data(updates["password"])

    conn = get_db_connection()
    try:
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])  # nosec B608
        values = list(updates.values())
        values.append(host)

        query = f"UPDATE switches SET {set_clause} WHERE host = ?"  # nosec B608
        cursor = conn.execute(query, tuple(values))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logger.error(f"Error en switches_db.update_switch_in_db para {host}: {e}")
        return 0
    finally:
        conn.close()


def delete_switch_from_db(host: str) -> int:
    """Elimina un switch de la base de datos. Devuelve el número de filas afectadas."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM switches WHERE host = ?", (host,))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logger.error(f"Error en switches_db.delete_switch_from_db para {host}: {e}")
        return 0
    finally:
        conn.close()


# --- Funciones para el Monitor ---


def get_switch_status(host: str) -> str | None:
    """
    Obtiene el 'last_status' de un switch específico desde la base de datos.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT last_status FROM switches WHERE host = ?", (host,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def update_switch_status(host: str, status: str, data: dict[str, Any] | None = None):
    """
    Actualiza el estado de un switch en la base de datos.
    Si el estado es 'online', también actualiza el hostname, modelo y firmware.
    """
    try:
        now = datetime.utcnow()
        update_data = {"last_status": status, "last_checked": now}

        if status == DeviceStatus.ONLINE and data:
            update_data["hostname"] = data.get("name")
            update_data["model"] = data.get("board-name")
            update_data["firmware"] = data.get("version")
            if data.get("mac_address"):
                update_data["mac_address"] = data.get("mac_address")

        update_switch_in_db(host, update_data)

    except Exception as e:
        logger.error(f"Error en switches_db.update_switch_status para {host}: {e}")


def get_enabled_switches_from_db() -> list[dict[str, Any]]:
    """
    Obtiene la lista de Switches activos desde la BD.
    """
    switches_to_monitor = []
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """SELECT host, username, password, api_port, api_ssl_port 
               FROM switches 
               WHERE is_enabled = TRUE"""
        )
        for row in cursor.fetchall():
            # Descifrar la contraseña
            data = dict(row)
            if data.get("password"):
                data["password"] = decrypt_data(data["password"])
            switches_to_monitor.append(data)

        conn.close()
    except sqlite3.Error as e:
        logger.error(f"No se pudo obtener la lista de Switches de la base de datos: {e}")
    return switches_to_monitor
