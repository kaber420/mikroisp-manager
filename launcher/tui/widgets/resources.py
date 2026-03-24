from textual.widgets import Static
from textual.app import ComposeResult
import psutil
from datetime import datetime

class ResourceWidget(Static):
    """Display System Resources (CPU, RAM, Disk)"""
    
    DEFAULT_CSS = """
    ResourceWidget {
        content-align: center middle;
    }
    """

    def on_mount(self) -> None:
        self.update_stats()
        self.set_interval(1.0, self.update_stats)

    def update_stats(self) -> None:
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Format Output
            lines = [
                f"[b]CPU:[/b] {cpu:.1f}%",
                f"[b]RAM:[/b] {mem.percent}% ({mem.used // (1024**2)}MB)",
                f"[b]Disk:[/b] {disk.free // (1024**3)}GB Free"
            ]
            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"Error: {e}")
