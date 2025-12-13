# app/db/logs_db.py
import sqlite3
from datetime import datetime
import os

from .base import get_stats_db_file


def get_log_connection():
    """Conecta a la DB de estadísticas del mes actual."""
    db_file = get_stats_db_file()
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS event_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_host TEXT NOT NULL,
            device_type TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    return conn


def add_event_log(host: str, device_type: str, event_type: str, message: str):
    conn = None
    try:
        conn = get_log_connection()
        conn.execute(
            "INSERT INTO event_logs (device_host, device_type, event_type, message) VALUES (?, ?, ?, ?)",
            (host, device_type, event_type, message),
        )
        conn.commit()
    except Exception as e:
        print(f"Error guardando log: {e}")
    finally:
        if conn:
            conn.close()


# --- NUEVAS FUNCIONES DE PAGINACIÓN ---


def get_event_logs_paginated(
    host_filter: str = None, page: int = 1, page_size: int = 10
):
    """Obtiene logs con paginación (LIMIT/OFFSET)."""
    conn = None
    try:
        conn = get_log_connection()
        offset = (page - 1) * page_size

        query = "SELECT * FROM event_logs"
        params = []

        if host_filter and host_filter != "all":
            query += " WHERE device_host = ?"
            params.append(host_filter)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        cursor = conn.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error leyendo logs: {e}")
        return []
    finally:
        if conn:
            conn.close()


def count_event_logs(host_filter: str = None) -> int:
    """Cuenta el total de logs para calcular el número de páginas."""
    conn = None
    try:
        conn = get_log_connection()
        query = "SELECT COUNT(*) FROM event_logs"
        params = []

        if host_filter and host_filter != "all":
            query += " WHERE device_host = ?"
            params.append(host_filter)

        cursor = conn.execute(query, tuple(params))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error contando logs: {e}")
        return 0
    finally:
        if conn:
            conn.close()
