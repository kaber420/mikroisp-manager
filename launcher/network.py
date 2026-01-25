# launcher/network.py
"""Utilidades de red."""

import socket


def get_lan_ip() -> str:
    """Detecta la IP LAN principal (no localhost)."""
    try:
        # Connect to a public DNS (doesn't send data) to get the interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 1.1.1.1 is Cloudflare DNS, 80 is port (doesn't matter if unreachable)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
