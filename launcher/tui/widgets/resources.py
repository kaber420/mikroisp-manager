try:
    import psutil
except ImportError:
    psutil = None

from rich.panel import Panel
from rich.table import Table
from rich import box
from ..styles import Styles

class ResourceWidget:
    def __init__(self):
        self.last_cpu = 0
        self.last_ram = 0

    def get_cpu_color(self, percentage):
        if percentage < 60: return Styles.CPU_NORMAL
        if percentage < 85: return Styles.CPU_HIGH
        return Styles.CPU_CRITICAL

    def render(self) -> Panel:
        if not psutil:
            return Panel("psutil not installed", title="Resources", box=box.ROUNDED)

        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # Memory
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used = mem.used / (1024 ** 3)
        ram_total = mem.total / (1024 ** 3)
        
        # Disk (Data partition)
        disk = psutil.disk_usage('.')
        disk_free = disk.free / (1024 ** 3)

        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(justify="right")

        # CPU Row
        grid.add_row(
            "💻 CPU:", 
            f"[{self.get_cpu_color(cpu_percent)}]{cpu_percent:.1f}%[/]"
        )
        
        # RAM Row
        grid.add_row(
            "🧠 RAM:", 
            f"[{Styles.RAM_NORMAL}]{ram_used:.1f}/{ram_total:.1f} GB ({ram_percent}%)"
        )

        # Disk Row
        grid.add_row(
            "💾 Disk:", 
            f"[{Styles.STATUS_OK}]{disk_free:.1f} GB Free[/]"
        )

        return Panel(
            grid,
            title="System Resources",
            border_style=Styles.PANEL_BORDER,
            box=box.ROUNDED
        )
