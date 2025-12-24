# app/api/stats/main.py
import sqlite3
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional

# --- RBAC: Stats is read-only, allow all authenticated users ---
from ...core.users import current_active_user
from ...models.user import User
from ...db.base import get_db_connection, get_stats_db_connection, get_stats_db_file

# --- ¡IMPORTACIÓN CORREGIDA! (Ahora desde '.models') ---
from .models import TopAP, TopCPE

router = APIRouter()


# --- Dependencias de DB (Lógica sin cambios) ---
def get_inventory_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()


def get_stats_db():
    conn = get_stats_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()


# --- Endpoints de la API (Lógica sin cambios) ---
@router.get("/stats/top-aps-by-airtime", response_model=List[TopAP])
def get_top_aps_by_airtime(
    limit: int = 5,
    conn: sqlite3.Connection = Depends(get_inventory_db),
    current_user: User = Depends(current_active_user),
):
    stats_db_file = get_stats_db_file()
    if not os.path.exists(stats_db_file):
        return []

    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
        query = """
            WITH LatestStats AS (
                SELECT 
                    ap_host, airtime_total_usage,
                    ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                FROM stats_db.ap_stats_history
                WHERE airtime_total_usage IS NOT NULL
            )
            SELECT a.hostname, a.host, s.airtime_total_usage
            FROM aps as a 
            JOIN LatestStats s ON a.host = s.ap_host AND s.rn = 1
            ORDER BY s.airtime_total_usage DESC 
            LIMIT ?;
        """
        cursor = conn.execute(query, (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


@router.get("/stats/top-cpes-by-signal", response_model=List[TopCPE])
def get_top_cpes_by_weak_signal(
    limit: int = 5,
    stats_conn: Optional[sqlite3.Connection] = Depends(get_stats_db),
    current_user: User = Depends(current_active_user),
):
    if not stats_conn:
        return []

    query = """
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
            FROM cpe_stats_history
            WHERE signal IS NOT NULL
        )
        SELECT cpe_hostname, cpe_mac, ap_host, signal
        FROM LatestCPEStats
        WHERE rn = 1
        ORDER BY signal ASC 
        LIMIT ?;
    """
    cursor = stats_conn.execute(query, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows


@router.get("/stats/cpe-count", response_model=Dict[str, int])
def get_cpe_total_count(
    conn: sqlite3.Connection = Depends(get_inventory_db),
    current_user: User = Depends(current_active_user),
):
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM cpes")
        count = cursor.fetchone()[0]
        return {"total_cpes": count}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


from ...db.logs_db import (
    get_event_logs_paginated,
    count_event_logs,
)  # Importamos las nuevas funciones

# ... (otros endpoints) ...


@router.get("/stats/events")
def get_dashboard_events(
    host: str = None,
    page: int = 1,  # Nuevo parámetro
    page_size: int = 10,  # Nuevo parámetro (default 10)
    conn: Optional[sqlite3.Connection] = Depends(get_stats_db),
    current_user: User = Depends(current_active_user),
):
    """
    Obtiene los logs paginados.
    """
    # Usamos las funciones de DB dedicadas en lugar de SQL crudo aquí
    logs = get_event_logs_paginated(host, page, page_size)
    total_records = count_event_logs(host)

    total_pages = (total_records + page_size - 1) // page_size

    return {
        "items": logs,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
