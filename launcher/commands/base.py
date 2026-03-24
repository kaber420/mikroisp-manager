import abc
import argparse

class BaseCommand(abc.ABC):
    """Clase base para comandos del launcher."""
    
    name = "base"
    help = "Comando base"

    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = parser
        self.add_arguments()

    def add_arguments(self):
        """Override para añadir argumentos al subparser."""
        pass

    @abc.abstractmethod
    def run(self, args: argparse.Namespace):
        """Lógica principal del comando."""
        pass
