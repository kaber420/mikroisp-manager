# app/db/base.py
import sqlite3
import os
from datetime import datetime
from typing import Optional  # <-- CORRECCIÓN: Importación añadida

# --- Constantes de la Base de Datos ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
INVENTORY_DB_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")


def get_stats_db_file() -> str:
    """Genera la ruta del archivo de estadísticas del mes actual."""
    now = datetime.utcnow()
    stats_dir = os.path.join(DATA_DIR, "db", "stats")
    os.makedirs(stats_dir, exist_ok=True)
    return os.path.join(stats_dir, f"stats_{now.strftime('%Y_%m')}.sqlite")


# --- Funciones de Conexión ---
def get_db_connection() -> sqlite3.Connection:
    """
    Establece una conexión con la base de datos de inventario
    y configura el row_factory para acceder a las columnas por nombre.
    Activa WAL mode para mejorar concurrencia.
    """
    # Ensure the db directory exists
    db_dir = os.path.dirname(INVENTORY_DB_FILE)
    os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(INVENTORY_DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # Mejora concurrencia
    conn.row_factory = sqlite3.Row
    return conn


def get_stats_db_connection() -> Optional[sqlite3.Connection]:
    """
    Establece una conexión con la base de datos de estadísticas del mes actual.
    Devuelve None si el archivo no existe.
    Activa WAL mode para mejorar concurrencia.
    """
    stats_db_file = get_stats_db_file()

    if not os.path.exists(stats_db_file):
        return None

    conn = sqlite3.connect(stats_db_file, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # Mejora concurrencia
    conn.row_factory = sqlite3.Row
    return conn
