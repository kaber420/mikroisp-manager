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
from .server import cleanup, start_api_server
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
        # Si usamos el flag --config, salimos para que el usuario reinicie limpio si quiere
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

    # Si SSL está habilitado pero Caddy no está corriendo, mostrar advertencia
    if is_production and not caddy_active:
        print("\n⚠️  HTTPS configurado pero Caddy no está activo.")
        if sys.platform == "win32":
            print("   Abre una terminal como Administrador y ejecuta: caddy run")
        else:
            print("   Ejecuta: sudo systemctl start caddy")

    # D. Arrancar logic
    port = os.getenv("UVICORN_PORT", "7777")
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()

    # Process management
    caddy_process = start_caddy_if_needed(is_production)
    if caddy_process:
        caddy_active = True

    # Leer workers para mostrar en banner
    workers = os.getenv("UVICORN_WORKERS", "4")

    # Obtener workers de monitoreo
    from app.utils.settings_utils import get_setting_sync
    monitor_workers = get_setting_sync("monitor_max_workers") or "10"

    print("-" * 60)
    if is_production and caddy_active:
        print("🚀 µMonitor Pro (Modo Producción - HTTPS)")
        print(f"   🏠 Local:     https://{hostname}.local")
        print(f"   📡 Network:   https://{lan_ip}")
        print(f"   🔌 Management: http://localhost:{port}")
        print(f"   ⚡ Workers:   {workers} (Web) | {monitor_workers} (Monitor)")
    else:
        print("🚀 µMonitor Pro (Modo Desarrollo/Local)")
        print(f"   🔌 Local:     http://localhost:{port}")
        print(f"   📡 Network:   http://{lan_ip}:{port}")
        print(f"   ⚡ Workers:   {workers} (Web) | {monitor_workers} (Monitor)")
        if is_production:
            print(
                "   ⚠️  HTTPS habilitado pero Caddy no responde. La web no cargará segura."
            )
        else:
            print("   ⚠️  HTTPS no activo. Algunas funciones pueden limitarse.")

    print("-" * 60)
    print("ℹ️  Para reconfigurar puerto base: python launcher.py --config")
    print("-" * 60)

    from app.scheduler import run_scheduler

    # Scheduler corre en subprocess, uvicorn en main process (para soportar workers)
    p_scheduler = multiprocessing.Process(target=run_scheduler, name="Scheduler")

    try:
        p_scheduler.start()
        time.sleep(1)

        # Uvicorn corre en el proceso principal para soportar múltiples workers
        start_api_server()

    except KeyboardInterrupt:
        cleanup(caddy_process, p_scheduler)
        sys.exit(0)
    finally:
        cleanup(caddy_process, p_scheduler)
        sys.exit(0)


if __name__ == "__main__":
    main()
