
import sys
import os
import multiprocessing
from rich.console import Console

sys.path.append(os.getcwd())

from launcher.tui.dashboard import Dashboard
from launcher.tui.widgets.resources import ResourceWidget
from launcher.tui.widgets.health import HealthWidget
from launcher.tui.widgets.logs import LogsWidget

print("Initializing Widgets...")
server_info = {
    "production": True,
    "local_url": "http://localhost:8000",
    "network_url": "http://192.168.1.5:8000",
    "port": "8000",
    "web_workers": "1",
    "monitor_workers": "1"
}
log_queue = multiprocessing.Queue()

res = ResourceWidget()
health = HealthWidget(server_info)
logs = LogsWidget(log_queue)

print("Initializing Dashboard...")
dash = Dashboard(server_info, res, health, logs)

print("Attempting to render...")
console = Console()
try:
    layout = dash.render()
    with console.capture() as capture:
        console.print(layout)
    print("Render successful.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("Render FAILED.")
