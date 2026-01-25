from .base import BaseCommand
from launcher.config import config_manager
import argparse

class ConfigCommand(BaseCommand):
    name = "config"
    help = "Gestión de configuración del launcher"

    def add_arguments(self):
        self.parser.add_argument("--set-headless", choices=["true", "false"], help="Activar/Desactivar modo headless por defecto")
        self.parser.add_argument("--show", action="store_true", help="Mostrar configuración actual")

    def run(self, args: argparse.Namespace):
        if args.set_headless:
            value = args.set_headless.lower() == "true"
            config_manager.set("headless", value)
            state = "ACTIVADO" if value else "DESACTIVADO"
            print(f"✅ Modo Headless por defecto: {state}")
            print(f"   (Guardado en {config_manager.config_path})")

        if args.show:
            print(f"📂 Archivo de configuración: {config_manager.config_path}")
            print("⚙️  Configuración actual:")
            for k, v in config_manager.config.items():
                print(f"   - {k}: {v}")
        
        if not args.set_headless and not args.show:
            self.parser.print_help()
