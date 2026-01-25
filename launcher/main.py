import multiprocessing
import os
import sys
import time
import argparse
import socket
from dotenv import load_dotenv

# Ensure app path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from launcher.constants import ENV_FILE
from launcher.user_setup import check_and_create_first_user
from launcher.network import get_lan_ip
from launcher.caddy import is_caddy_running, start_caddy_if_needed
from launcher.server import start_api_process

# Commands
from launcher.commands.diagnose import DiagnoseCommand
from launcher.commands.management import ManagementCommand
from launcher.commands.setup import SetupCommand

# TUI
from launcher.tui import TUIApp

def cleanup(caddy_process, scheduler_process, uvicorn_process):
    print("Stopping services...")
    if scheduler_process and scheduler_process.is_alive():
        scheduler_process.terminate()
    if uvicorn_process:
        # It's a Popen object
        uvicorn_process.terminate()
        try:
             uvicorn_process.wait(timeout=5)
        except:
             uvicorn_process.kill()
    if caddy_process:
        caddy_process.terminate()

def run_server(args):
    # --- Verificaciones Previas ---
    load_dotenv(ENV_FILE)
    check_and_create_first_user()

    is_production = os.getenv("APP_ENV") == "production"
    caddy_active = is_caddy_running()
    
    # Init Logging Queue
    log_queue = multiprocessing.Queue()

    # --- Start Caddy ---
    caddy_process = start_caddy_if_needed(is_production)
    if caddy_process:
        caddy_active = True
    
    # --- Prepare Server Info ---
    port = os.getenv("UVICORN_PORT", "7777")
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    
    # Monitor Workers Setting
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
        "web_workers": os.getenv("UVICORN_WORKERS", "4"),
        "monitor_workers": monitor_workers
    }

    # --- Start Processes ---
    # 1. Scheduler
    from app.scheduler import run_scheduler
    p_scheduler = multiprocessing.Process(
        target=run_scheduler, 
        args=(log_queue,),
        name="Scheduler"
    )
    
    # 2. Uvicorn
    p_uvicorn = None

    try:
        p_scheduler.start()
        p_uvicorn = start_api_process(log_queue)
        
        if args.headless:
            # Headless Mode: Simple blocking wait
            print(f"Server running in HEADLESS mode.")
            print(f"Management: {server_info['local_url']}")
            while True:
                time.sleep(1)
        else:
            # TUI Mode
            tui = TUIApp(log_queue, server_info)
            tui.run()

    except KeyboardInterrupt:
        pass
    finally:
        cleanup(caddy_process, p_scheduler, p_uvicorn)
        sys.exit(0)

def main():
    multiprocessing.freeze_support()
    
    parser = argparse.ArgumentParser(description="µMonitor Pro Launcher")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Instantiate and register commands
    commands = {}

    # Diagnose
    diag_parser = subparsers.add_parser("diagnose", help="Diagnóstico del sistema")
    commands["diagnose"] = DiagnoseCommand(diag_parser)

    # Manage
    mgmt_parser = subparsers.add_parser("manage", help="Gestión del sistema")
    commands["manage"] = ManagementCommand(mgmt_parser)

    # Setup
    setup_parser = subparsers.add_parser("setup", help="Asistente de configuración")
    commands["setup"] = SetupCommand(setup_parser)

    # Server Arguments (Default)
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin interfaz gráfica (TUI)")

    args = parser.parse_args()

    if args.command in commands:
        commands[args.command].run(args)
    else:
        # Default action: Run Server
        run_server(args)

if __name__ == "__main__":
    main()
