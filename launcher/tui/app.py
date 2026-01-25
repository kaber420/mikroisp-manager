from textual.app import App, ComposeResult

from .screens.dashboard import Dashboard
from .screens.menu import MenuScreen
from launcher.config import config_manager
from launcher.commands.management import ManagementCommand
from launcher.commands.diagnose import DiagnoseCommand
import argparse
import io
import contextlib
import logging
import time

class MonitorApp(App):
    """µMonitor Pro TUI Launcher"""
    
    CSS_PATH = "tcss/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "toggle_menu", "Menu"),
        ("d", "toggle_dark", "Dark Mode"),
    ]

    def __init__(self, log_queue, service_manager):
        super().__init__()
        self.log_queue = log_queue
        self.service_manager = service_manager
        self.server_info = service_manager.server_info

    def on_mount(self) -> None:
        self.install_screen(Dashboard(self.log_queue, self.server_info), name="dashboard")
        self.push_screen("dashboard")

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_quit(self) -> None:
        self.exit()

    def action_toggle_menu(self) -> None:
        headless = config_manager.get("headless", False)
        status = "ON" if headless else "OFF"
        
        items = [
            (f"Headless Mode (Start): {status}", "toggle_headless"),
            ("Restart Web Server", "restart_web"),
            ("Diagnose System", "run_diagnose"),
            ("Clean Logs (>7 days)", "clean_logs"),
            ("Optimize DB (Vacuum)", "vacuum_db"),
            ("Exit Launcher", "exit_app")
        ]
        
        def handle_menu_result(result):
            if result:
                # Dispatch using getattr logic
                method = getattr(self, f"_action_{result}", None)
                if method:
                    method()

        self.push_screen(MenuScreen(items), handle_menu_result)

    # --- Actions ---

    def _action_exit_app(self):
        self.exit()

    def _action_toggle_headless(self):
        current = config_manager.get("headless", False)
        new_val = not current
        config_manager.set("headless", new_val)
        self._log(f"Config Changed: Headless -> {new_val}")

    def _action_restart_web(self):
        self._log("Restarting Web Server...", "WARNING")
        # Run in worker to not block UI? 
        # For simplicity, we run here, might freeze UI briefly.
        # Ideally: self.run_worker(self.service_manager.restart_web)
        try:
             self.service_manager.restart_web()
             self._log("Web Server Restarted", "INFO")
        except Exception as e:
             self._log(f"Restart Failed: {e}", "ERROR")

    def _action_run_diagnose(self):
        self._log("Running Diagnosis...", "INFO")
        cmd = DiagnoseCommand(argparse.ArgumentParser())
        output = self._capture_output(cmd.run, argparse.Namespace())
        self._log_output(output)

    def _action_clean_logs(self):
        self._log("Cleaning Logs...", "INFO")
        cmd = ManagementCommand(argparse.ArgumentParser())
        ns = argparse.Namespace(clean_logs=True, vacuum_db=False)
        output = self._capture_output(cmd.run, ns)
        self._log_output(output)

    def _action_vacuum_db(self):
        self._log("Optimizing DB...", "INFO")
        cmd = ManagementCommand(argparse.ArgumentParser())
        ns = argparse.Namespace(clean_logs=False, vacuum_db=True)
        output = self._capture_output(cmd.run, ns)
        self._log_output(output)

    # --- Helpers ---

    def _capture_output(self, func, *args):
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
             try:
                func(*args)
             except Exception as e:
                print(f"Error: {e}")
        return f.getvalue()

    def _log_output(self, text):
        for line in text.split('\n'):
            if line.strip():
                self._log(line.strip(), "INFO")

    def _log(self, msg, level="INFO"):
        r = logging.LogRecord("TUI", logging.getLevelName(level), "", 0, msg, (), None)
        r.created = time.time()
        self.log_queue.put(r)
