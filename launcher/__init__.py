# launcher/__init__.py
"""Launcher package para µMonitor Pro."""

from .setup_wizard import run_setup_wizard
from .user_setup import check_and_create_first_user
from .server import start_api_server, cleanup
from .caddy import is_caddy_running, start_caddy_if_needed, apply_caddy_config, generate_caddyfile
from .network import get_lan_ip
from .constants import ENV_FILE

__all__ = [
    "run_setup_wizard",
    "check_and_create_first_user",
    "start_api_server",
    "cleanup",
    "is_caddy_running",
    "start_caddy_if_needed",
    "apply_caddy_config",
    "generate_caddyfile",
    "get_lan_ip",
    "ENV_FILE",
]
