# launcher/server.py
"""Gestión del servidor Uvicorn."""

import os
import subprocess

from dotenv import load_dotenv

from .constants import ENV_FILE


def start_api_server() -> None:
    """Inicia el servidor Uvicorn."""
    import uvicorn

    # Recargar ENV por si cambió el puerto
    load_dotenv(ENV_FILE, override=True)

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", 7777))
    workers = int(os.getenv("UVICORN_WORKERS", 4))

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            server_header=False,  # --- SEGURIDAD: No revelar 'server: uvicorn' ---
            proxy_headers=True,  # --- PROXY: Confiar en headers (X-Forwarded-For) de Caddy ---
            forwarded_allow_ips="*",  # --- PROXY: Permitir IPs de cualquier proxy (Caddy es local) ---
        )
    except KeyboardInterrupt:
        pass


def cleanup(
    caddy_process: subprocess.Popen | None, scheduler_process
) -> None:
    """Limpia procesos al cerrar."""
    print("\n🛑 Apagando...")
    if caddy_process:
        print("   Terminando Caddy...")
        caddy_process.terminate()
    if scheduler_process and scheduler_process.is_alive():
        scheduler_process.terminate()
        scheduler_process.join(timeout=5)
