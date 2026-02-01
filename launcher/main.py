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
from launcher.commands.config import ConfigCommand
from launcher.config import config_manager

# TUI
from launcher.tui import TUIApp

def run_server(args):
    # --- Verificaciones Previas ---
    # Init Logging Queue
    log_queue = multiprocessing.Queue()
    
    # Configure logging for the main process to use the queue
    from launcher.log_queue import configure_process_logging
    configure_process_logging(log_queue)
    
    # Initialize Service Manager
    from launcher.services import ServiceManager
    service_manager = ServiceManager(log_queue, args)

    try:
        # Start Services
        service_manager.start_all()
        
        # Mode is already resolved in main() and stored in args.headless
        is_headless = args.headless
        
        if is_headless:
            # Headless Mode: Log Monitor
            info = service_manager.server_info
            print(f"Server running in HEADLESS mode.")
            print(f"Management: {info['local_url']}")
            print("-" * 50)
            print(" OPCIONES DE RECUPERACIÓN:")
            print(" 1. Solo esta vez (Rescue):   python launcher/main.py --tui")
            print(" 2. Cambiar para siempre:     python launcher/main.py --tui --save")
            print("-" * 50)
            print("Showing live logs (Ctrl+C to stop)...")
            
            import queue
            while True:
                try:
                    # Non-blocking get with timeout to allow checking for signals
                    record = log_queue.get(timeout=0.5)
                    # Simple formatting: [LEVEL] Source: Message
                    print(f"[{record.levelname}] {record.name}: {record.msg}")
                except queue.Empty:
                    continue
        else:
            # TUI Mode
            # Pass service_manager instead of just server_info
            tui = TUIApp(log_queue, service_manager)
            tui.run()

    except KeyboardInterrupt:
        pass
    finally:
        service_manager.stop_all()
        sys.exit(0)

def main():
    multiprocessing.freeze_support()
    
    # Load .env early for fallback values
    load_dotenv(ENV_FILE)
    
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

    # Config
    config_parser = subparsers.add_parser("config", help="Configuración del Launcher")
    commands["config"] = ConfigCommand(config_parser)

    # Server Arguments (Default)
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin interfaz gráfica (Headless)")
    parser.add_argument("--tui", action="store_true", help="Forzar ejecución con interfaz gráfica (TUI)")
    parser.add_argument("--save", action="store_true", help="Guardar la preferencia de modo (--tui o --headless) en la configuración")
    parser.add_argument("--webworkers", type=int, default=None, help="Número de workers de Uvicorn (ej: --webworkers 4)")
    parser.add_argument("--port", type=int, default=None, help="Puerto de escucha de Uvicorn (ej: --port 8100)")

    args = parser.parse_args()

    # --- Resolve Headless Mode ---
    # Priority: 1. CLI flags, 2. Saved config, 3. Default (False)
    target_headless = None
    if args.tui:
        is_headless = False
        target_headless = False
    elif args.headless:
        is_headless = True
        target_headless = True
    else:
        is_headless = config_manager.get("headless", False)
        target_headless = None

    # --- Resolve Web Workers ---
    # Priority: 1. CLI, 2. config_manager, 3. .env
    if args.webworkers is not None:
        web_workers = args.webworkers
    else:
        saved_workers = config_manager.get("web_workers")
        if saved_workers is not None:
            web_workers = saved_workers
        else:
            web_workers = int(os.getenv("UVICORN_WORKERS", "1"))

    # --- Resolve Port ---
    # Priority: 1. CLI, 2. config_manager, 3. .env
    if args.port is not None:
        port = args.port
    else:
        saved_port = config_manager.get("port")
        if saved_port is not None:
            port = saved_port
        else:
            port = int(os.getenv("UVICORN_PORT", "7777"))

    # --- Handle --save ---
    if args.save:
        save_msg_parts = []
        if target_headless is not None:
            config_manager.set("headless", target_headless)
            mode_str = "HEADLESS" if target_headless else "TUI"
            save_msg_parts.append(f"Modo: {mode_str}")
        if args.webworkers is not None:
            config_manager.set("web_workers", args.webworkers)
            save_msg_parts.append(f"Workers: {args.webworkers}")
        if args.port is not None:
            config_manager.set("port", args.port)
            save_msg_parts.append(f"Puerto: {args.port}")
        
        if save_msg_parts:
            print(f"✅ Configuración guardada: {', '.join(save_msg_parts)}")

    # Inject resolved values into args for run_server and ServiceManager
    args.headless = is_headless
    args.web_workers = web_workers
    args.resolved_port = port

    if args.command in commands:
        commands[args.command].run(args)
    else:
        # Default action: Run Server
        run_server(args)

if __name__ == "__main__":
    main()

