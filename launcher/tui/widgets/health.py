from textual.widgets import Static
from launcher.caddy import is_caddy_running

class HealthWidget(Static):
    """Display System Health Status"""
    
    def __init__(self, service_manager):
        super().__init__()
        self.service_manager = service_manager

    def on_mount(self) -> None:
        self.check_health()
        self.set_interval(2.0, self.check_health)

    def check_health(self) -> None:
        # Check process status
        uvicorn_alive = False
        p_uvicorn = self.service_manager.processes.get("uvicorn")
        if p_uvicorn:
            # Handle both multiprocessing.Process and subprocess.Popen
            if hasattr(p_uvicorn, 'is_alive'):
                uvicorn_alive = p_uvicorn.is_alive()
            elif hasattr(p_uvicorn, 'poll'):
                uvicorn_alive = p_uvicorn.poll() is None

        scheduler_alive = False
        p_scheduler = self.service_manager.processes.get("scheduler")
        if p_scheduler and p_scheduler.is_alive():
            scheduler_alive = True
            
        # Caddy check
        caddy_running = is_caddy_running()

        # Formatting
        uvicorn_status = "[green]ONLINE[/]" if uvicorn_alive else "[red]DOWN[/]"
        scheduler_status = "[green]ONLINE[/]" if scheduler_alive else "[red]DOWN[/]"
        caddy_status = "[green]ONLINE[/]" if caddy_running else "[red]DOWN[/]"

        # Static info
        server_info = self.service_manager.server_info
        web_workers = server_info.get("web_workers", 0)
        monitor_workers = server_info.get("monitor_workers", 0)
        
        # Network info (local only)
        lan_ip = server_info.get("network_url", "Unknown")

        lines = [
            f"[b]LAN URL:[/b] {lan_ip}",
            f"[b]Api Server:[/b] {uvicorn_status}",
            f"[b]Scheduler:[/b] {scheduler_status}",
            f"[b]Caddy Proxy:[/b] {caddy_status}",
            f"[b]Workers:[/b] Web({web_workers}) / Monitor({monitor_workers})"
        ]
        self.update("\n".join(lines))
