import multiprocessing
import os
import sys
import time
import subprocess
import threading
import logging
from dotenv import load_dotenv
from launcher.constants import ENV_FILE
from launcher.network import get_lan_ip
from launcher.user_setup import check_and_create_first_user

class ServiceManager:
    def __init__(self, log_queue, args):
        self.log_queue = log_queue
        self.args = args
        self.processes = {
            "docker_logs": None
        }
        self.server_info = {}
        self._init_server_info()

    def _init_server_info(self):
        """Prepara la información estática del servidor."""
        load_dotenv(ENV_FILE)
        
        # En contenedor, la creación interactiva del primer usuario se maneja internamente
        # o mediante variables de entorno (ADMIN_EMAIL, etc.) en bootstrap.py.
        # Desactivamos check_and_create_first_user en el host para evitar problemas de imports circulares y de base de datos local sqlite.
        # check_and_create_first_user(interactive=interactive_mode)

        self.is_production = os.getenv("APP_ENV") == "production"

        port = getattr(self.args, 'resolved_port', None) or int(os.getenv("UVICORN_PORT", "7777"))
        web_workers = getattr(self.args, 'web_workers', None) or int(os.getenv("UVICORN_WORKERS", "1"))
        
        lan_ip = get_lan_ip()
        
        monitor_workers = "10"

        # Parse Database Info desde .env para mostrar en TUI
        db_url = os.getenv("DATABASE_URL")
        db_type = "SQLite"
        db_host = "Local File"
        
        if db_url and "postgres" in db_url:
            db_type = "PostgreSQL"
            try:
                from urllib.parse import urlparse
                parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
                db_host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
            except Exception:
                db_host = "Unknown"

        self.server_info = {
            "production": self.is_production,
            "local_url": f"https://localhost" if self.is_production else f"http://localhost:{port}",
            "network_url": f"https://{lan_ip}" if self.is_production else f"http://{lan_ip}:{port}",
            "port": str(port),
            "web_workers": str(web_workers),
            "monitor_workers": monitor_workers,
            "db_type": db_type,
            "db_host": db_host
        }

    def start_all(self):
        """Inicia todos los servicios en Docker Compose."""
        self._log("🚀 Iniciando el despliegue de OmniWISP Pro en Docker...", "INFO")
        
        try:
            # Ejecutar docker compose up -d en el host
            subprocess.run(
                ["docker", "compose", "up", "-d"], 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            self._log("✅ Contenedores Docker iniciados con éxito.", "INFO")
            
            # Arrancar el capturador de logs en vivo
            self.start_docker_log_streamer()
        except Exception as e:
            self._log(f"❌ Error al desplegar Docker Compose: {e}", "ERROR")

    def start_docker_log_streamer(self):
        """Arranca un hilo para escuchar y canalizar los logs de docker compose a la cola del Launcher."""
        if self.processes.get("docker_logs"):
            return

        cmd = ["docker", "compose", "logs", "-f", "--tail=100"]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            self.processes["docker_logs"] = process

            def log_reader(pipe):
                try:
                    with pipe:
                        for line in iter(pipe.readline, ''):
                            if line.strip():
                                source = "DockerCompose"
                                msg = line.strip()
                                if " | " in msg:
                                    parts = msg.split(" | ", 1)
                                    source = parts[0].strip()
                                    msg = parts[1].strip()

                                record = logging.LogRecord(
                                    name=source,
                                    level=logging.INFO,
                                    pathname="docker",
                                    lineno=0,
                                    msg=msg,
                                    args=(),
                                    exc_info=None
                                )
                                self.log_queue.put(record)
                except ValueError:
                    pass

            t = threading.Thread(target=log_reader, args=(process.stdout,), daemon=True)
            t.start()
            self._log("📡 Streaming de logs de contenedores activo.", "INFO")
        except Exception as e:
            self._log(f"⚠️ Error iniciando streaming de logs: {e}", "ERROR")

    def restart_web(self):
        """Reinicia el servicio web (contenedor backend)."""
        self._log("♻️ Reiniciando contenedor backend de FastAPI...", "WARNING")
        try:
            subprocess.run(
                ["docker", "compose", "restart", "backend"], 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            self._log("✅ Contenedor backend reiniciado con éxito.", "INFO")
        except Exception as e:
            self._log(f"❌ Error al reiniciar backend: {e}", "ERROR")

    def stop_all(self):
        """Detiene todos los contenedores de Docker Compose."""
        self._log("🛑 Deteniendo servicios de Docker compose...", "INFO")
        
        # Detener log streamer
        p = self.processes.get("docker_logs")
        if p:
            try:
                p.terminate()
                p.wait(timeout=2)
            except:
                pass
            self.processes["docker_logs"] = None

        try:
            subprocess.run(
                ["docker", "compose", "down"], 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            self._log("✅ Contenedores de Docker compose detenidos con éxito.", "INFO")
        except Exception as e:
            self._log(f"❌ Error al detener Docker compose: {e}", "ERROR")

    def _log(self, msg, level="INFO"):
        r = logging.LogRecord("ServiceMgr", logging.getLevelName(level), "", 0, msg, (), None)
        r.created = time.time()
        self.log_queue.put(r)

    def get_app_status(self):
        """Lee el archivo de estado generado por la app."""
        import json
        status_file = "data/umanager_status.json"
        
        default_status = {
            "cache": {"redict_connected": False},
            "bots": {"mode": "unknown", "client_bot": {}, "tech_bot": {}},
            "timestamp": 0
        }

        if not os.path.exists(status_file):
            return default_status

        try:
            mtime = os.path.getmtime(status_file)
            if time.time() - mtime > 15: # 15s stale
                return default_status

            with open(status_file, "r") as f:
                return json.load(f)
        except Exception:
            return default_status
