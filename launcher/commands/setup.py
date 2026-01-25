from .base import BaseCommand
import argparse
from launcher.setup_wizard import run_setup_wizard

class SetupCommand(BaseCommand):
    name = "setup"
    help = "Ejecuta el wizard de configuración inicial."

    def add_arguments(self):
        self.parser.add_argument("--network-only", action="store_true", help="Solo configurar red")
        self.parser.add_argument("--ssl-only", action="store_true", help="Solo configurar SSL")

    def run(self, args: argparse.Namespace):
        # TODO: Pass args to wizard or split wizard logic
        run_setup_wizard()
