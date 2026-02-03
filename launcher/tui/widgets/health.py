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
        db_type = server_info.get("db_type", "Unknown")
        db_host = server_info.get("db_host", "Unknown")
        
        # Network info (local only)
        lan_ip = server_info.get("network_url", "Unknown")
        
        # --- App Status (File IPC) ---
        app_status = self.service_manager.get_app_status()
        
        # Cache
        c_stats = app_status.get("cache", {})
        is_redict = c_stats.get("redict_connected", False)
        cache_status = "[green]REDICT[/]" if is_redict else "[yellow]MEMORY[/]"
        
        # Bots
        b_stats = app_status.get("bots", {})
        c_bot = b_stats.get("client_bot", {})
        t_bot = b_stats.get("tech_bot", {})
        
        c_run = c_bot.get("running", False)
        t_run = t_bot.get("running", False)
        
        # Logic for "ONLINE" vs "PARTIAL" vs "OFFLINE"
        if not c_bot.get("enabled") and not t_bot.get("enabled"):
             bots_status = "[gray]DISABLED[/]"
        elif c_run and t_run:
             bots_status = "[green]ONLINE[/]"
        elif c_run or t_run:
             bots_status = "[yellow]PARTIAL[/]"
        else:
             bots_status = "[red]OFFLINE[/]"
             
        # Optional details line if needed, or just keep it clean
        mode = b_stats.get("mode", "auto").upper()
        bots_detail = f"({mode})"

        lines = [
            f"[b]LAN URL:[/b] {lan_ip}",
            f"[b]Api Server:[/b] {uvicorn_status}",
            f"[b]Scheduler:[/b] {scheduler_status}",
            f"[b]Caddy Proxy:[/b] {caddy_status}",
            f"[b]Workers:[/b] Web({web_workers}) / Monitor({monitor_workers})",
            f"[b]Database:[/b] {db_type} ({db_host})",
            "",
            f"[b]Cache:[/b] {cache_status}",
            f"[b]Bots:[/b] {bots_status} {bots_detail}"
        ]
        self.update("\n".join(lines))
