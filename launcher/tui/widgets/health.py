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
        import subprocess

        def get_container_state(service_name: str) -> str:
            try:
                res = subprocess.run(
                    ["docker", "compose", "ps", service_name, "--format", "{{.State}}"],
                    capture_output=True,
                    text=True
                )
                state = res.stdout.strip().lower()
                if "running" in state:
                    return "[green]ONLINE[/]"
                elif "exited" in state or "paused" in state:
                    return "[yellow]STOPPED[/]"
                elif "restarting" in state:
                    return "[yellow]RESTARTING[/]"
                else:
                    return "[red]DOWN[/]"
            except Exception:
                return "[red]DOWN[/]"

        # Check container status
        uvicorn_status = get_container_state("backend")
        scheduler_status = get_container_state("scheduler")
        caddy_status = get_container_state("caddy")

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

