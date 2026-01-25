# launcher/tui.py
import queue
import time
from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich import box
from rich.align import Align

class DashboardTUI:
    def __init__(self, log_queue, server_info):
        self.log_queue = log_queue
        self.server_info = server_info
        self.console = Console()
        self.logs = []
        self.max_logs = 100
        self.layout = Layout()
        self.setup_layout()

    def setup_layout(self):
        """Define la estructura del layout principal"""
        self.layout.split(
            Layout(name="header", size=10),
            Layout(name="logs", ratio=1),
        )

    def generate_header(self):
        """Genera el panel de información superior"""
        info = self.server_info
        
        # Tabla principal del header
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)

        # Título
        status_text = Text("🚀 µMonitor Pro - Dashboard", style="bold cyan")
        if info.get("production"):
            status_text.append(" (Producción - HTTPS)", style="bold green")
        else:
            status_text.append(" (Desarrollo)", style="bold yellow")
            
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Info Grid
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_row("🏠 Local:", f"{info['local_url']}")
        info_table.add_row("📡 Network:", f"{info['network_url']}")
        info_table.add_row("🔌 Management:", f"http://localhost:{info['port']}")
        
        # Workers Grid
        workers_table = Table(show_header=False, box=None, padding=(0, 2))
        workers_table.add_row("⚡ Web Workers:", f"[bold cyan]{info['web_workers']}[/]")
        workers_table.add_row("🔍 Monitor Workers:", f"[bold magenta]{info['monitor_workers']}[/]")
        
        # Layout del Header interno
        header_content = Table.grid(expand=True)
        header_content.add_row(status_text, Text(f"🕒 {time_str}", style="dim"))
        header_content.add_row(info_table, workers_table)

        return Panel(
            header_content,
            title="Estado del Sistema",
            border_style="blue",
            box=box.ROUNDED
        )

    def generate_logs(self):
        """Genera el panel de logs desplazable"""
        log_text = Text()
        for timestamp, level, name, msg in self.logs[-self.max_logs:]:
            # Estilo por nivel
            style = "white"
            icon = "•"
            if level == "INFO":
                style = "green"
                icon = "ℹ"
            elif level == "WARNING":
                style = "yellow"
                icon = "⚠"
            elif level == "ERROR":
                style = "bold red"
                icon = "❌"
            elif level == "CRITICAL":
                style = "bold red on white"
                icon = "🔥"

            line = Text(f"{timestamp}", style="dim")
            line.append(f" {icon} ")
            line.append(f"[{name}] ", style="bold blue")
            line.append(msg, style=style)
            line.append("\n")
            log_text.append(line)

        return Panel(
            log_text,
            title="Live Logs",
            border_style="white",
            box=box.ROUNDED
        )

    def run(self):
        """Loop principal de la UI"""
        # Creacion inicial de paneles
        self.layout["header"].update(self.generate_header())
        self.layout["logs"].update(self.generate_logs())
        
        # Control de actualización del header
        last_header_update = 0
        
        with Live(self.layout, refresh_per_second=10, screen=True) as live:
            try:
                while True:
                    current_time = time.time()
                    
                    # Solo actualizar logs si hay nuevos
                    if self.process_queue():
                         self.layout["logs"].update(self.generate_logs())
                    
                    # Actualizar header cada segundo para el reloj
                    if current_time - last_header_update >= 1.0:
                        self.layout["header"].update(self.generate_header())
                        last_header_update = current_time
                        
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
    
    def process_queue(self):
        """Lee logs de la cola. Retorna True si hubo nuevos logs."""
        has_new = False
        try:
            while True:
                record = self.log_queue.get_nowait()
                timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
                # Clean message
                msg = record.getMessage()
                self.logs.append((timestamp, record.levelname, record.name, msg))
                if len(self.logs) > self.max_logs:
                    self.logs.pop(0)
                has_new = True
        except queue.Empty:
            pass
        return has_new
