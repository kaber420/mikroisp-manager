# app/services/monitor_job.py
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests

from .monitor_service import MonitorService

# Configuración
MAX_WORKERS = 10

# Configuración del logging
logger = logging.getLogger("MonitorJob")


def notify_api_update():
    """
    Envía una señal HTTP a la API para que actualice los WebSockets.
    Se ejecuta al finalizar cada ciclo de escaneo.
    """
    try:
        # Leemos el puerto del entorno o usamos 8000 por defecto
        port = os.getenv("UVICORN_PORT", "8000")
        # Llamamos al endpoint interno que creamos en main.py
        url = f"http://127.0.0.1:{port}/api/internal/notify-monitor-update"
        requests.post(url, timeout=2)
    except Exception:
        # Si falla (ej. la API se está reiniciando), no detenemos el monitor
        pass


def run_monitor_cycle():
    """
    Ejecuta UN ciclo de monitoreo de routers y APs.
    Esta función es llamada periódicamente por APScheduler.
    """
    monitor_service = MonitorService()
    logger.info("--- Iniciando ciclo de escaneo ---")

    try:
        devices = monitor_service.get_active_devices()

        aps = devices["aps"]
        routers = devices["routers"]

        # --- BLOQUE: AUTO-LIMPIEZA DE ROUTERS (DESHABILITADO) ---
        # NOTA: La limpieza secuencial se removió porque causaba bloqueos fatales
        # si un router no respondía (no hay timeout por defecto en sockets).
        # La limpieza ahora ocurre de forma asíncrona dentro de cada worker.
        # ----------------------------------------------

        if not aps and not routers:
            logger.info("No hay dispositivos para monitorear.")
        else:
            # 1. Procesar dispositivos en paralelo (Bloqueante hasta que terminen)
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                if aps:
                    executor.map(monitor_service.check_ap, aps)
                if routers:
                    executor.map(monitor_service.check_router, routers)

            # 2. Notificar a la API que hay datos frescos
            logger.info(
                "Ciclo terminado. Notificando a la API para actualización en tiempo real..."
            )
            notify_api_update()

        logger.info("--- Ciclo de escaneo completado ---")

    except Exception as e:
        logger.exception(f"Error en el ciclo del monitor: {e}")
