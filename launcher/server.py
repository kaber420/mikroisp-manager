# launcher/server.py
"""Gestión del servidor Uvicorn via Subprocess."""

import os
import subprocess
import sys
import threading
import logging

from dotenv import load_dotenv
from .constants import ENV_FILE

def start_api_process(log_queue, workers: int | None = None, port: int | None = None) -> subprocess.Popen:
    """
    Inicia uvicorn como un subproceso independiente y captura su salida
    para redirigirla a la cola de logs.
    
    Args:
        log_queue: Cola de logs para capturar salida.
        workers: Número de workers (opcional, fallback a UVICORN_WORKERS env).
        port: Puerto de escucha (opcional, fallback a UVICORN_PORT env).
    """
    load_dotenv(ENV_FILE, override=True)

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    
    # Use passed values or fall back to env vars
    final_port = str(port) if port is not None else os.getenv("UVICORN_PORT", "7777")
    final_workers = str(workers) if workers is not None else os.getenv("UVICORN_WORKERS", "4")
    
    # Comando para ejecutar uvicorn desde el mismo entorno python
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--host", host,
        "--port", final_port,
        "--workers", final_workers,
        "--log-level", "info",
        "--no-server-header",
        "--proxy-headers",
        "--forwarded-allow-ips", "*"
    ]

    # Iniciar proceso con PIPEs para capturar logs y DEVNULL para stdin (fix crash)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1  # Line buffered
    )

    # Hilos para capturar stdout y stderr
    def log_reader(pipe, level):
        try:
            with pipe:
                for line in iter(pipe.readline, ''):
                    if line.strip():
                        # Crear un LogRecord manual para enviarlo a la cola
                        record = logging.LogRecord(
                            name="uvicorn",
                            level=level,
                            pathname="subprocess",
                            lineno=0,
                            msg=line.strip(),
                            args=(),
                            exc_info=None
                        )
                        log_queue.put(record)
        except ValueError:
            pass  # Pipe cerrado

    # Uvicorn suele mandar todo a stderr o stdout dependiendo de configuracion, 
    # pero capturamos ambos por si acaso.
    t_out = threading.Thread(target=log_reader, args=(process.stdout, logging.INFO), daemon=True)
    t_err = threading.Thread(target=log_reader, args=(process.stderr, logging.INFO), daemon=True)
    
    t_out.start()
    t_err.start()

    return process

def cleanup(
    caddy_process: subprocess.Popen | None, scheduler_process, uvicorn_process
) -> None:
    """Limpia procesos al cerrar."""
    if caddy_process:
        caddy_process.terminate()
        
    if scheduler_process and scheduler_process.is_alive():
        scheduler_process.terminate()
        scheduler_process.join(timeout=2)
        
    if uvicorn_process:
        # Si es un Popen object
        if isinstance(uvicorn_process, subprocess.Popen):
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                uvicorn_process.kill()
        # Si es un multiprocessing.Process (legacy/fallback)
        elif hasattr(uvicorn_process, 'is_alive') and uvicorn_process.is_alive():
            uvicorn_process.terminate()
            uvicorn_process.join(timeout=2)
