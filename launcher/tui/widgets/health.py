from rich.panel import Panel
from rich.table import Table
from rich import box
from ..styles import Styles
import socket

class HealthWidget:
    def __init__(self, server_info):
        self.server_info = server_info
        self.checks = {
            "db": "UNKNOWN",
            "net": "UNKNOWN",
            "web": "UNKNOWN"
        }

    def check_network(self):
        try:
            # Check DNS
            socket.create_connection(("1.1.1.1", 53), timeout=1)
            return True
        except OSError:
            return False

    def update(self):
        # TODO: Real async checks usually go here or outside. 
        # For now we do simple quick checks.
        self.checks["net"] = "OK" if self.check_network() else "ERROR"
        self.checks["web"] = "OK" if self.server_info.get("production") else "DEV"
        # DB check would require app context or separate checker

    def render(self) -> Panel:
        self.update()
        
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=1)
        grid.add_column(justify="right")

        # Net
        net_style = Styles.STATUS_OK if self.checks["net"] == "OK" else Styles.STATUS_ERROR
        net_icon = "🟢" if self.checks["net"] == "OK" else "🔴"
        grid.add_row("🌐 Internet", f"{net_icon}")

        # Web
        web_style = Styles.STATUS_OK if self.checks["web"] == "OK" else Styles.STATUS_WARNING
        web_icon = "🟢" if self.checks["web"] == "OK" else "🟡"
        grid.add_row("🔒 HTTPS/Web", f"{web_icon}")
        
        # Workers
        workers = self.server_info.get("web_workers", "0")
        grid.add_row("⚡ Web Workers", f"{workers}")

        # Monitor Workers
        monitor_workers = self.server_info.get("monitor_workers", "0")
        grid.add_row("🔍 Mon. Workers", f"{monitor_workers}")

        return Panel(
            grid,
            title="Health Status",
            border_style=Styles.PANEL_BORDER,
            box=box.ROUNDED
        )
