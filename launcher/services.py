import multiprocessing
import os
import sys
import time
from launcher.caddy import is_caddy_running, start_caddy_if_needed
from launcher.server import start_api_process
from launcher.network import get_lan_ip
from launcher.user_setup import check_and_create_first_user
from dotenv import load_dotenv
from launcher.constants import ENV_FILE
import socket

class ServiceManager:
    def __init__(self, log_queue, args):
        self.log_queue = log_queue
        self.args = args
        self.processes = {
            "caddy": None,
            "scheduler": None,
            "uvicorn": None
        }
        self.server_info = {}
        self._init_server_info()

    def _init_server_info(self):
        """Prepara la información estática del servidor."""
        load_dotenv(ENV_FILE)
        check_and_create_first_user()

        self.is_production = os.getenv("APP_ENV") == "production"
        caddy_active = is_caddy_running() # Check initial state

        port = os.getenv("UVICORN_PORT", "7777")
        lan_ip = get_lan_ip()
        
        # Monitor Workers Setting
        monitor_workers = "10"
        try:
            from app.utils.settings_utils import get_setting_sync
            monitor_workers = get_setting_sync("monitor_max_workers") or "10"
        except Exception:
            pass

        self.server_info = {
            "production": self.is_production, # Caddy active might change, but mode usually doesn't
            "local_url": f"https://localhost" if self.is_production else f"http://localhost:{port}",
            "network_url": f"https://{lan_ip}" if self.is_production else f"http://{lan_ip}:{port}",
            "port": port,
            "web_workers": os.getenv("UVICORN_WORKERS", "4"),
            "monitor_workers": monitor_workers
        }

    def start_all(self):
        """Inicia todos los servicios."""
        self.start_caddy()
        self.start_scheduler()
        self.start_uvicorn()

    def start_caddy(self):
        """Inicia Caddy si es necesario."""
        # En producción, intentamos iniciar caddy si no está ya corriendo
        # start_caddy_if_needed maneja la lógica de chequear si ya corre
        self.processes["caddy"] = start_caddy_if_needed(self.is_production)
    
    def start_scheduler(self):
        """Inicia el Scheduler en un proceso separado."""
        from app.scheduler import run_scheduler
        p = multiprocessing.Process(
            target=run_scheduler, 
            args=(self.log_queue,),
            name="Scheduler"
        )
        p.start()
        self.processes["scheduler"] = p
        self._log("Scheduler started", "INFO")

    def start_uvicorn(self):
        """Inicia Uvicorn (API Server)."""
        # start_api_process returns a Popen object (subprocess)
        p = start_api_process(self.log_queue)
        self.processes["uvicorn"] = p
        self._log("Uvicorn Web Server started", "INFO")

    def restart_web(self):
        """Reinicia el servicio web (Uvicorn)."""
        self._log("Restarting Web Server...", "WARNING")
        if self.processes["uvicorn"]:
            self._stop_process("uvicorn")
        
        # Wait a bit
        time.sleep(1)
        self.start_uvicorn()
        self._log("Web Server restarted successfully.", "INFO")

    def stop_all(self):
        """Detiene todos los servicios."""
        self._log("Stopping all services...", "INFO")
        self._stop_process("scheduler")
        self._stop_process("uvicorn")
        self._stop_process("caddy")

    def _stop_process(self, name):
        p = self.processes.get(name)
        if not p:
            return

        try:
            if hasattr(p, 'terminate'):
                p.terminate()
                # For multiprocessing.Process
                if hasattr(p, 'join'):
                    p.join(timeout=2)
                # For subprocess.Popen
                elif hasattr(p, 'wait'):
                    p.wait(timeout=2)
            
            # Verificar si sigue vivo
            is_alive = False
            if hasattr(p, 'is_alive'):
                 is_alive = p.is_alive()
            elif hasattr(p, 'poll'):
                 is_alive = p.poll() is None
            
            if is_alive:
                 if hasattr(p, 'kill'):
                     p.kill()
        except Exception as e:
            self._log(f"Error stopping {name}: {e}", "ERROR")
        finally:
            self.processes[name] = None

    def _log(self, msg, level="INFO"):
        # Helper interno para enviar a la queue
        import logging
        r = logging.LogRecord("ServiceMgr", logging.getLevelName(level), "", 0, msg, (), None)
        r.created = time.time()
        self.log_queue.put(r)
