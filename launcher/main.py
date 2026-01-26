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
    
    # Initialize Service Manager
    from launcher.services import ServiceManager
    service_manager = ServiceManager(log_queue, args)

    try:
        # Start Services
        service_manager.start_all()
        
        # Mode is already resolved in main() and stored in args.headless
        is_headless = args.headless
        
        if is_headless:
            # Headless Mode: Simple blocking wait
            info = service_manager.server_info
            print(f"Server running in HEADLESS mode.")
            print(f"Management: {info['local_url']}")
            print("-" * 50)
            print(" OPCIONES DE RECUPERACIÓN:")
            print(" 1. Solo esta vez (Rescue):   python launcher/main.py --tui")
            print(" 2. Cambiar para siempre:     python launcher/main.py --tui --save")
            print("-" * 50)
            while True:
                time.sleep(1)
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

    args = parser.parse_args()

    # Combinar argumentos CLI y persistencia
    # Lógica de prioridad:
    # 1. Flags explícitos (--tui o --headless)
    # 2. Configuración guardada
    
    target_setting = None # Para guardar si se solicita

    if args.tui:
        is_headless = False
        target_setting = False
    elif args.headless:
        is_headless = True
        target_setting = True
    else:
        # Si no hay flags explícitos, usar configuración guardada
        is_headless = config_manager.get("headless", False)
        target_setting = None

    # Manejar guardado si se solicita y hubo una intención explícita
    if args.save and target_setting is not None:
        config_manager.set("headless", target_setting)
        mode_str = "HEADLESS" if target_setting else "TUI"
        print(f"✅ Configuración actualizada: Modo {mode_str} guardado por defecto.")

    # Inyectar el valor final en args para que run_server lo use si es necesario
    # (aunque run_server recalcula un poco, es mejor pasarlo limpio o manejarlo en run_server)
    # Para ser consistente con la estructura existente, modificaremos run_server para aceptar 'is_headless' explícito
    # O mejor, "monkey-patch" args.headless con el valor calculado para no cambiar la firma de run_server
    args.headless = is_headless

    if args.command in commands:
        commands[args.command].run(args)
    else:
        # Default action: Run Server
        run_server(args)

if __name__ == "__main__":
    main()
