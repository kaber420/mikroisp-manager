from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from datetime import datetime
from .styles import Styles

class Dashboard:
    def __init__(self, server_info, resources_widget, health_widget, logs_widget):
        self.server_info = server_info
        self.resources = resources_widget
        self.health = health_widget
        self.logs = logs_widget
        self.layout = Layout()
        
        # Menu State
        self.show_menu = False
        self.menu_items = []
        self.selected_index = 0
        
        self.setup_layout()

    def setup_layout(self):
        # Header (Top), Body (Middle)
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )
        
        # Split Main into Sidebar (Stats) and Content (Logs)
        self.layout["main"].split_row(
            Layout(name="sidebar", size=35),
            Layout(name="content", ratio=1),
        )
        
        # Split Sidebar into Resources and Health
        self.layout["sidebar"].split(
            Layout(name="resources", size=10),
            Layout(name="health", size=10),
            Layout(name="info"),  # Extra info or spacing
        )

    def generate_header(self):
        info = self.server_info
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)

        title = Text("🚀 µMonitor Pro", style=Styles.TITLE)
        if info.get("production"):
            title.append(" [PROD]", style="bold green")
        else:
            title.append(" [DEV]", style="bold yellow")
            
        time_str = datetime.now().strftime("%H:%M:%S")
        grid.add_row(title, Text(f"⏰ {time_str}", style="dim"))

        return Panel(
            grid,
            border_style=Styles.HEADER_BORDER,
            box=box.HEAVY_HEAD
        )

    def generate_info_panel(self):
        info = self.server_info
        grid = Table.grid(expand=True)
        grid.add_column()
        
        grid.add_row("🏠 Local:")
        grid.add_row(info.get('local_url', 'N/A'), style="blue link " + info.get('local_url', ''))
        grid.add_row("")
        grid.add_row("📡 Net:")
        grid.add_row(info.get('network_url', 'N/A'), style="blue link " + info.get('network_url', ''))
        
        return Panel(
            grid,
            title="Access Info",
            border_style="blue",
            box=box.ROUNDED
        )

    def render_menu(self):
        from rich.align import Align
        
        grid = Table.grid(padding=1)
        grid.add_column()
        
        grid.add_row(Text("Use ↑/↓ to navigate, ENTER to select", style="dim italic"), end_section=True)
        grid.add_row("") 

        for idx, (label, action) in enumerate(self.menu_items):
            style = "bold white on blue" if idx == self.selected_index else "white"
            prefix = "👉 " if idx == self.selected_index else "   "
            grid.add_row(Text(f"{prefix}{label}", style=style))

        panel = Panel(
            grid,
            title="Menu Principal",
            subtitle="[ESC] Close",
            border_style="cyan",
            box=box.DOUBLE,
            width=60,
            padding=(1, 2)
        )
        return Align.center(panel, vertical="middle")

    def generate_footer(self):
        """Genera una barra de estado inferior con atajos"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center")
        
        shortcuts = [
            ("m", "Menu"),
            ("Ctrl+c", "Stop"),
        ]
        
        text = Text()
        for key, desc in shortcuts:
            text.append(f" [{key}] ", style="bold white on blue")
            text.append(f" {desc} ", style="white on black")
            text.append("  ")
        
        grid.add_row(text)
            
        return Panel(grid, title="Shortcuts", border_style="dim")
        # Since I don't have a footer layout slot in setup_layout, I will append this to the info panel or make a new slot.
        # Let's verify setup_layout first.

    def render(self) -> Layout:
        if self.show_menu:
            return self.render_menu()
            
        # Update components
        self.layout["header"].update(self.generate_header())
        
        self.layout["resources"].update(self.resources.render())
        self.layout["health"].update(self.health.render())
        self.layout["info"].update(self.generate_info_panel())
        
        self.layout["content"].update(self.logs.render())
        self.layout["footer"].update(self.generate_footer())
        
        return self.layout
