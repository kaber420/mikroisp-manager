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
            "uvicorn": None,
            "tech_bot": None,
            "client_bot": None
        }
        self.server_info = {}
        self._init_server_info()

    def _init_server_info(self):
        """Prepara la información estática del servidor."""
        load_dotenv(ENV_FILE)
        check_and_create_first_user()

        self.is_production = os.getenv("APP_ENV") == "production"
        caddy_active = is_caddy_running() # Check initial state

        # Use resolved values from args if available, else fallback to env
        port = getattr(self.args, 'resolved_port', None) or int(os.getenv("UVICORN_PORT", "7777"))
        web_workers = getattr(self.args, 'web_workers', None) or int(os.getenv("UVICORN_WORKERS", "1"))
        
        lan_ip = get_lan_ip()
        
        # Monitor Workers Setting
        monitor_workers = "10"
        try:
            from app.utils.settings_utils import get_setting_sync
            monitor_workers = get_setting_sync("monitor_max_workers") or "10"
        except Exception:
            pass

        # Parse Database Info
        db_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_SYNC")
        db_type = "SQLite"
        db_host = "Local File"
        
        if db_url and "postgres" in db_url:
            db_type = "PostgreSQL"
            try:
                # Basic parsing to hide credentials
                # format: postgresql://user:pass@host:port/db
                from urllib.parse import urlparse
                parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
                db_host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
            except Exception:
                db_host = "Unknown"

        self.server_info = {
            "production": self.is_production, # Caddy active might change, but mode usually doesn't
            "local_url": f"https://localhost" if self.is_production else f"http://localhost:{port}",
            "network_url": f"https://{lan_ip}" if self.is_production else f"http://{lan_ip}:{port}",
            "port": str(port),
            "web_workers": str(web_workers),
            "monitor_workers": monitor_workers,
            "db_type": db_type,
            "db_host": db_host
        }

    def start_all(self):
        """Inicia todos los servicios."""
        self.start_caddy()
        self.start_scheduler()
        self.start_uvicorn()
        # Bots now integrated in main.py (hybrid architecture)
        # self.start_tech_bot()
        # self.start_client_bot()

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
        # Get resolved values from args
        workers = getattr(self.args, 'web_workers', None)
        port = getattr(self.args, 'resolved_port', None)
        
        # start_api_process returns a Popen object (subprocess)
        p = start_api_process(self.log_queue, workers=workers, port=port)
        self.processes["uvicorn"] = p
        self._log(f"Uvicorn Web Server started (workers={workers}, port={port})", "INFO")

    def start_tech_bot(self):
        """Inicia el Tech Bot."""
        from app.utils.settings_utils import get_setting_sync
        token = get_setting_sync("telegram_bot_token")
        if not token:
            self._log("Tech Bot skipped: Token not set", "WARNING")
            return

        env = os.environ.copy()
        env["TECH_BOT_TOKEN"] = token
        # Add app/bot to PYTHONPATH so it can find 'core' modules
        bot_path = os.path.join(os.getcwd(), 'app', 'bot')
        env["PYTHONPATH"] = bot_path + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [sys.executable, "-m", "app.bot.bot_tech"]
        self.processes["tech_bot"] = self._start_bot_process(cmd, env, "tech_bot")
        self._log("Tech Bot started", "INFO")

    def start_client_bot(self):
        """Inicia el Client Bot."""
        from app.utils.settings_utils import get_setting_sync
        token = get_setting_sync("client_bot_token")
        if not token:
            self._log("Client Bot skipped: Token not set", "WARNING")
            return

        env = os.environ.copy()
        env["CLIENT_BOT_TOKEN"] = token
        # Add app/bot to PYTHONPATH
        bot_path = os.path.join(os.getcwd(), 'app', 'bot')
        env["PYTHONPATH"] = bot_path + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [sys.executable, "-m", "app.bot.bot_client.bot_client"]
        self.processes["client_bot"] = self._start_bot_process(cmd, env, "client_bot")
        self._log("Client Bot started", "INFO")

    def _start_bot_process(self, cmd, env, name):
        import subprocess
        import threading
        import logging

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            env=env,
            text=True,
            bufsize=1
        )

        def log_reader(pipe, level):
             try:
                with pipe:
                    for line in iter(pipe.readline, ''):
                        if line.strip():
                            record = logging.LogRecord(
                                name=name,
                                level=level,
                                pathname="subprocess",
                                lineno=0,
                                msg=line.strip(),
                                args=(),
                                exc_info=None
                            )
                            self.log_queue.put(record)
             except ValueError:
                pass

        t_out = threading.Thread(target=log_reader, args=(process.stdout, logging.INFO), daemon=True)
        t_err = threading.Thread(target=log_reader, args=(process.stderr, logging.ERROR), daemon=True)
        
        t_out.start()
        t_err.start()
        
        return process

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
        self._stop_process("tech_bot")
        self._stop_process("client_bot")
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

    def get_app_status(self):
        """Lee el archivo de estado generado por la app."""
        import json
        status_file = "/tmp/umanager_status.json"
        
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
