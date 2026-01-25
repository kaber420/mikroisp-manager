import time
from rich.live import Live
from rich.console import Console
from .dashboard import Dashboard
from .widgets.resources import ResourceWidget
from .widgets.health import HealthWidget
from .widgets.logs import LogsWidget
from .input import InputHelper
from launcher.config import config_manager
from launcher.commands.management import ManagementCommand
from launcher.commands.diagnose import DiagnoseCommand
import argparse
import io
import contextlib

class TUIApp:
    def __init__(self, log_queue, service_manager):
        self.log_queue = log_queue
        self.service_manager = service_manager
        self.server_info = service_manager.server_info
        self.console = Console()
        
        # Initialize Widgets
        self.resources_widget = ResourceWidget()
        self.health_widget = HealthWidget(self.server_info)
        self.logs_widget = LogsWidget(log_queue)
        
        # Initialize Dashboard
        self.dashboard = Dashboard(
            self.server_info,
            self.resources_widget,
            self.health_widget,
            self.logs_widget
        )
        
        self._setup_menu()

    def _setup_menu(self):
        headless = config_manager.get("headless", False)
        status = "ON" if headless else "OFF"
        
        self.dashboard.menu_items = [
            (f"Headless Mode (Start): {status}", self._toggle_headless),
            ("Restart Web Server", self._restart_web),
            ("Diagnose System", self._run_diagnose),
            ("Clean Logs (>7 days)", self._clean_logs),
            ("Optimize DB (Vacuum)", self._vacuum_db),
            ("Exit Launcher", self._exit_app)
        ]

    def _restart_web(self):
        self.log_queue.put(self._make_log("Restarting Web Server...", "WARNING"))
        self.service_manager.restart_web()
        self.log_queue.put(self._make_log("Web Server Restarted", "INFO"))

    def _toggle_headless(self):
        current = config_manager.get("headless", False)
        new_val = not current
        config_manager.set("headless", new_val)
        self.log_queue.put(self._make_log(f"Config Changed: Headless -> {new_val}"))
        self._setup_menu() # Refresh label

    def _run_diagnose(self):
        self.log_queue.put(self._make_log("Running Diagnosis...", "INFO"))
        cmd = DiagnoseCommand(argparse.ArgumentParser())
        output = self._capture_output(cmd.run, argparse.Namespace())
        self._log_output(output)

    def _clean_logs(self):
        self.log_queue.put(self._make_log("Cleaning Logs...", "INFO"))
        cmd = ManagementCommand(argparse.ArgumentParser())
        ns = argparse.Namespace(clean_logs=True, vacuum_db=False)
        output = self._capture_output(cmd.run, ns)
        self._log_output(output)

    def _vacuum_db(self):
        self.log_queue.put(self._make_log("Optimizing DB...", "INFO"))
        cmd = ManagementCommand(argparse.ArgumentParser())
        ns = argparse.Namespace(clean_logs=False, vacuum_db=True)
        output = self._capture_output(cmd.run, ns)
        self._log_output(output)

    def _exit_app(self):
        raise KeyboardInterrupt

    def _capture_output(self, func, *args):
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
             try:
                func(*args)
             except Exception as e:
                print(f"Error: {e}")
        return f.getvalue()

    def _log_output(self, text):
        import logging
        for line in text.split('\n'):
            if line.strip():
                # Mock a log record
                self.log_queue.put(self._make_log(line.strip(), "INFO"))

    def _make_log(self, msg, level="INFO"):
        # Helper to create a fake LogRecord object since our queue expects it
        import logging
        r = logging.LogRecord("TUI", logging.getLevelName(level), "", 0, msg, (), None)
        r.created = time.time()
        return r

    def handle_input(self, key):
        if not key: return
        
        d = self.dashboard
        
        if d.show_menu:
            if key == 'q' or key == 'KEY_ESC': # Esc
                d.show_menu = False
            elif key == 'KEY_UP' or key == 'A': # Up (A fallback if raw)
                d.selected_index = max(0, d.selected_index - 1)
            elif key == 'KEY_DOWN' or key == 'B': # Down (B fallback if raw)
                d.selected_index = min(len(d.menu_items) - 1, d.selected_index + 1)
            elif key == '\r' or key == '\n': # Enter
                label, action = d.menu_items[d.selected_index]
                if action:
                    action()
        else:
            if key == 'm' or key == 'c':
                d.show_menu = True
            elif key == 'q' or key == 'KEY_ESC':
                # Confirm exit?
                self._exit_app()

    def run(self):
        """Main Loop"""
        with InputHelper() as input_helper:
            with Live(self.dashboard.render(), refresh_per_second=4, screen=True) as live:
                try:
                    while True:
                        # Input
                        try:
                            key = input_helper.get_key()
                            self.handle_input(key)
                        except Exception as e:
                            with open("logs/tui_input_error.log", "a") as f:
                                f.write(f"{datetime.now()} Input Error: {e}\n")

                        # Update data (Logs are consumed here)
                        self.logs_widget.process_queue()
                        
                        # Refresh Layout
                        live.update(self.dashboard.render())
                        
                        time.sleep(0.05)
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    import traceback
                    with open("logs/tui_crash.log", "a") as f:
                        f.write(f"{datetime.now()} TUI Crash: {e}\n")
                        f.write(traceback.format_exc())
