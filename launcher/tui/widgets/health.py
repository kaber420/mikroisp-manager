from textual.widgets import Static
import socket

class HealthWidget(Static):
    """Display System Health Status"""
    
    def __init__(self, server_info):
        super().__init__()
        self.server_info = server_info

    def on_mount(self) -> None:
        self.check_health()
        self.set_interval(5.0, self.check_health)

    def check_network(self) -> bool:
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1)
            return True
        except OSError:
            return False

    def check_health(self) -> None:
        net_status = "[green]ONLINE[/]" if self.check_network() else "[red]OFFLINE[/]"
        web_status = "[green]RUNNING[/]" # Doing simple check for now
        
        web_workers = self.server_info.get("web_workers", 0)
        monitor_workers = self.server_info.get("monitor_workers", 0)
        url = self.server_info.get("local_url", "Unknown")

        lines = [
            f"[b]Network:[/b] {net_status}",
            f"[b]Web Server:[/b] {web_status}",
            f"[b]Web Workers:[/b] {web_workers}",
            f"[b]Monitor Workers:[/b] {monitor_workers}",
            f"[b]URL:[/b] {url}"
        ]
        self.update("\n".join(lines))
