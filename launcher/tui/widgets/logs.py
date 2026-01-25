from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime
import queue

class LogsWidget:
    def __init__(self, log_queue, max_logs=100):
        self.log_queue = log_queue
        self.max_logs = max_logs
        self.logs = []

    def process_queue(self):
        has_new = False
        try:
            while True:
                record = self.log_queue.get_nowait()
                timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
                msg = record.getMessage()
                # Basic cleaning/shortening could happen here
                self.logs.append((timestamp, record.levelname, record.name, msg))
                if len(self.logs) > self.max_logs:
                    self.logs.pop(0)
                has_new = True
        except queue.Empty:
            pass
        return has_new

    def render(self) -> Panel:
        log_text = Text()
        # Show last N logs that fit (approx)
        visible_logs = self.logs[-20:] 
        
        for timestamp, level, name, msg in visible_logs:
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
            line.append(f"[{name}] ", style="blue")
            line.append(msg, style=style)
            line.append("\n")
            log_text.append(line)

        return Panel(
            log_text,
            title="Live Logs",
            border_style="white",
            box=box.ROUNDED
        )
