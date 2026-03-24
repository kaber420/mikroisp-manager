from textual.widgets import RichLog
from rich.text import Text
from datetime import datetime
import queue

class LogsWidget(RichLog):
    """Display Application Logs"""

    def __init__(self, log_queue) -> None:
        super().__init__(markup=True, wrap=True)
        self.log_queue = log_queue
        self.border_title = "Logs"

    def on_mount(self) -> None:
        # Start a worker to poll logs non-blocking
        self.set_interval(0.1, self.poll_logs)

    def poll_logs(self) -> None:
        try:
            while True:
                record = self.log_queue.get_nowait()
                timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
                
                # Format log based on level
                level = record.levelname
                msg = record.getMessage()
                
                color = "white"
                if level == "INFO": color = "green"
                elif level == "WARNING": color = "yellow"
                elif level == "ERROR": color = "red"
                
                log_line = f"[{color}][{timestamp}] {level}: {msg}[/]"
                self.write(Text.from_markup(log_line))
        except queue.Empty:
            pass
