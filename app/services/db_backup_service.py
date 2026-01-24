import datetime
import logging
import os
import sqlite3
import shutil
import time

# Configura logger local
logger = logging.getLogger("DBBackupService")

# Rutas - asumiendo ejecución desde root o app
BASE_DIR = os.getcwd() # Debería ser root del proyecto cuando corre la app
DB_FILE = os.path.join(BASE_DIR, "data", "db", "inventory.sqlite")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")
RETENTION_DAYS = 30

def run_db_backup():
    """
    Función helper para ser llamada por el scheduler.
    """
    success = perform_db_backup(backup_type="auto")
    if success:
        clean_old_backups(RETENTION_DAYS)

def clean_old_backups(days_to_keep: int):
    """Deletes backups older than N days."""
    now = time.time()
    cutoff = now - (days_to_keep * 86400)
    
    if not os.path.exists(BACKUP_DIR):
        return

    logger.info(f"Aplicando política de retención: borrando backups más antiguos de {days_to_keep} días...")
    
    count = 0
    for filename in os.listdir(BACKUP_DIR):
        if not filename.startswith("backup_") or not filename.endswith(".sqlite"):
            continue
            
        filepath = os.path.join(BACKUP_DIR, filename)
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                logger.info(f"Borrado: {filename}")
                count += 1
        except OSError as e:
            logger.error(f"Error borrando {filename}: {e}")
            
    if count > 0:
        logger.info(f"Limpieza completada. Se eliminaron {count} archivos.")

def perform_db_backup(backup_type: str = "manual"):
    """
    Performs a backup using SQLite 'VACUUM INTO' for safe hot backups.
    """
    if not os.path.exists(DB_FILE):
        logger.error(f"Archivo de base de datos no encontrado en: {DB_FILE}")
        return False

    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{backup_type}_{timestamp}.sqlite"
    backup_path = os.path.abspath(os.path.join(BACKUP_DIR, backup_filename))

    logger.info(f"Iniciando respaldo de BD ({backup_type})...")
    
    try:
        # Connect to the DB and use VACUUM INTO
        # This requires SQLite 3.27+
        con = sqlite3.connect(DB_FILE)
        
        # Execute VACUUM INTO
        try:
            sql_query = f"VACUUM INTO '{backup_path}'" 
            con.execute(sql_query)
            con.close()
            logger.info(f"✅ Respaldo de BD exitoso: {backup_filename}")
            return True
        except sqlite3.OperationalError as e:
            con.close()
            logger.error(f"Error SQLite VACUUM: {e}")
            # Fallback copy
            logger.warning("Intentando copia simple (fallback)...")
            shutil.copy2(DB_FILE, backup_path)
            logger.info("✅ Copia de respaldo exitosa (fallback logic).")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error General en Respaldo BD: {e}")
        return False
