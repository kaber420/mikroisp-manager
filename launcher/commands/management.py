import os
import glob
import time
import sqlite3
from .base import BaseCommand

class ManagementCommand(BaseCommand):
    name = "manage"
    help = "Comandos de gestión (clean-logs, vacuum-db, etc)."

    def add_arguments(self):
        self.parser.add_argument("--clean-logs", action="store_true", help="Limpiar logs de más de 7 días")
        self.parser.add_argument("--vacuum-db", action="store_true", help="Optimizar base de datos")

    def run(self, args):
        if not (args.clean_logs or args.vacuum_db):
            self.parser.print_help()
            return

        if args.clean_logs:
            self.clean_logs()
        
        if args.vacuum_db:
            self.vacuum_db()

    def clean_logs(self):
        print("🧹 Limpiando logs antiguos (>7 días)...")
        log_dir = "logs"
        if not os.path.exists(log_dir):
            print("   Directorio logs no existe.")
            return

        now = time.time()
        days_7 = 7 * 86400
        count = 0
        
        for f in glob.glob(os.path.join(log_dir, "*.log")):
            if os.stat(f).st_mtime < (now - days_7):
                try:
                    os.remove(f)
                    print(f"   Eliminado: {f}")
                    count += 1
                except Exception as e:
                    print(f"   Error eliminando {f}: {e}")
        
        print(f"✅ Se eliminaron {count} archivos de log.")

    def vacuum_db(self):
        print("💾 Optimizando base de datos (VACUUM)...")
        db_path = os.path.join("data", "db", "inventory.sqlite")
        if not os.path.exists(db_path):
            print("❌ Base de datos no encontrada.")
            return

        try:
            conn = sqlite3.connect(db_path)
            conn.execute("VACUUM")
            conn.close()
            print("✅ Base de datos optimizada.")
        except Exception as e:
            print(f"❌ Error durante VACUUM: {e}")
