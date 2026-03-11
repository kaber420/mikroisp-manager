import os

# --- Constantes de la Base de Datos ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
INVENTORY_DB_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")

# Note: get_db_connection and get_stats_db_connection have been removed.
# Please use app.db.engine.get_session (async) or app.db.engine_sync.get_sync_session (sync)
