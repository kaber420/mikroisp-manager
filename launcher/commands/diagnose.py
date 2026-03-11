import os
import socket
import sqlite3
from .base import BaseCommand
from launcher.constants import ENV_FILE

class DiagnoseCommand(BaseCommand):
    name = "diagnose"
    help = "Ejecuta un diagnóstico del sistema y sale."

    def run(self, args):
        print("🔍 Ejecutando Diagnóstico de µMonitor Pro...\n")
        
        checks = [
            ("Archivo .env", self.check_env),
            ("Base de Datos", self.check_db),
            ("Puerto Web", self.check_port),
            ("Permisos de Logs", self.check_logs)
        ]
        
        all_ok = True
        for name, func in checks:
            try:
                ok, msg = func()
                status = "✅" if ok else "❌"
                print(f"{status} {name}: {msg}")
                if not ok: all_ok = False
            except Exception as e:
                print(f"❌ {name}: Error inesperado - {e}")
                all_ok = False
                
        print("\n" + ("🎉 Todo parece correcto." if all_ok else "⚠️  Se encontraron problemas."))

    def check_env(self):
        if os.path.exists(ENV_FILE):
            return True, "Encontrado"
        return False, "No existe (Ejecuta 'setup')"

    def check_db(self):
        db_path = os.path.join("data", "db", "inventory.sqlite")
        if not os.path.exists(db_path):
            return False, "No encontrada"
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
            return True, "Conexión exitosa"
        except Exception as e:
            return False, str(e)

    def check_port(self):
        # Check if port is OPEN (listening) which means app is running, 
        # or CLOSED which means available for binding?
        # Diagnose usually checks if requirements are met.
        # Let's check if we can bind to it (if app not running) or if it is already taken.
        # Ideally we want to know if the configured port is valid.
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
        port = int(os.getenv("UVICORN_PORT", "7777"))
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            return True, f"Puerto {port} está activo (App posiblemente corriendo)"
        else:
            return True, f"Puerto {port} disponible para uso"

    def check_logs(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return False, "Directorio no existe"
        if not os.access(log_dir, os.W_OK):
            return False, "Sin permisos de escritura"
        return True, "Escritura permitida"
