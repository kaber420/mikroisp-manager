import time
from rich.live import Live
from rich.console import Console
from .dashboard import Dashboard
from .widgets.resources import ResourceWidget
from .widgets.health import HealthWidget
from .widgets.logs import LogsWidget

class TUIApp:
    def __init__(self, log_queue, server_info):
        self.log_queue = log_queue
        self.server_info = server_info
        self.console = Console()
        
        # Initialize Widgets
        self.resources_widget = ResourceWidget()
        self.health_widget = HealthWidget(server_info)
        self.logs_widget = LogsWidget(log_queue)
        
        # Initialize Dashboard
        self.dashboard = Dashboard(
            server_info,
            self.resources_widget,
            self.health_widget,
            self.logs_widget
        )

    def run(self):
        """Main Loop"""
        with Live(self.dashboard.render(), refresh_per_second=4, screen=True) as live:
            try:
                while True:
                    # Update data (Logs are consumed here)
                    self.logs_widget.process_queue()
                    
                    # Refresh Layout
                    live.update(self.dashboard.render())
                    
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
