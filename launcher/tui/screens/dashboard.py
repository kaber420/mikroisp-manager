from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer
from ..widgets.resources import ResourceWidget
from ..widgets.health import HealthWidget
from ..widgets.logs import LogsWidget

class Dashboard(Screen):
    """Main Dashboard Screen"""
    
    def __init__(self, log_queue, server_info):
        super().__init__()
        self.log_queue = log_queue
        self.server_info = server_info

    def compose(self) -> ComposeResult:
        yield Header()
        yield ResourceWidget()
        yield HealthWidget(self.server_info)
        yield LogsWidget(self.log_queue)
        yield Footer()
