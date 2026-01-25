# launcher/main.py
"""Punto de entrada principal de µMonitor Pro."""

import logging
import multiprocessing
import os
import socket
import sys
import time

from dotenv import load_dotenv

from .constants import ENV_FILE
from .caddy import is_caddy_running, start_caddy_if_needed
from .network import get_lan_ip
from .server import cleanup
from .setup_wizard import run_setup_wizard
from .user_setup import check_and_create_first_user

# --- Configuración del logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [Launcher] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    """Punto de entrada principal del launcher."""
    # A. Si el usuario pide configurar O si no existe el archivo .env
    if "--config" in sys.argv or not os.path.exists(ENV_FILE):
        run_setup_wizard()
        if "--config" in sys.argv:
            print("Reinicia el launcher para aplicar los cambios.")
            sys.exit(0)

    # B. Cargar configuración
    load_dotenv(ENV_FILE)

    # C. Inicializar BD y Usuario
    check_and_create_first_user()

    # --- Verificación de HTTPS (Caddy) ---
    is_production = os.getenv("APP_ENV") == "production"
    caddy_active = is_caddy_running()

    if is_production and not caddy_active:
        print("\n⚠️  HTTPS configurado pero Caddy no está activo.")
        # Nota: estos prints iniciales se verán antes del TUI, lo cual está bien.
        if sys.platform == "win32":
            print("   Abre una terminal como Administrador y ejecuta: caddy run")
        else:
            print("   Ejecuta: sudo systemctl start caddy")

    # D. Preparar datos para TUI
    port = os.getenv("UVICORN_PORT", "7777")
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    
    # Process management
    caddy_process = start_caddy_if_needed(is_production)
    if caddy_process:
        caddy_active = True

    workers = os.getenv("UVICORN_WORKERS", "4")

    # Obtener workers de monitoreo
    # MOVIDO: Importar aquí para evitar side-effects al spawnear procesos
    monitor_workers = "10"
    try:
        from app.utils.settings_utils import get_setting_sync
        monitor_workers = get_setting_sync("monitor_max_workers") or "10"
    except Exception:
        pass
    
    server_info = {
        "production": is_production and caddy_active,
        "local_url": f"https://{hostname}.local" if is_production and caddy_active else f"http://localhost:{port}",
        "network_url": f"https://{lan_ip}" if is_production and caddy_active else f"http://{lan_ip}:{port}",
        "port": port,
        "web_workers": workers,
        "monitor_workers": monitor_workers
    }

    # E. Configurar Orquestación (Colas y Procesos)
    log_queue = multiprocessing.Queue()
    
    # Importaciones diferidas para el spawn
    from app.scheduler import run_scheduler
    from launcher.tui import DashboardTUI

    # Scheduler Process (Sigue usando Multiprocessing porque es código interno nuestro)
    p_scheduler = multiprocessing.Process(
        target=run_scheduler, 
        args=(log_queue,),
        name="Scheduler"
    )
    
    # Uvicorn Process (Ahora usa Popen via helper para capturar logs y evitar stdin crash)
    from launcher.server import start_api_process
    # Nota: start_api_process ya inicia el proceso, no necesitamos .start()
    p_uvicorn = None

    try:
        p_scheduler.start()
        # Iniciar Uvicorn
        p_uvicorn = start_api_process(log_queue)
        
        # F. Iniciar TUI (Bloqueante, corre en Main Process)
        tui = DashboardTUI(log_queue, server_info)
        tui.run()

    except KeyboardInterrupt:
        pass
    finally:
        cleanup(caddy_process, p_scheduler, p_uvicorn)
        sys.exit(0)


if __name__ == "__main__":
    main()
