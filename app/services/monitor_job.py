
import asyncio
import logging
import os

import httpx

from app.db.engine import async_session_maker
from app.db.engine_sync import get_sync_session
from app.services.settings_service import SettingsService

from .monitor_service import MonitorService

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
        httpx.post(url, timeout=2)
    except Exception:
        # Si falla (ej. la API se está reiniciando), no detenemos el monitor
        pass


def run_monitor_cycle():
    """
    Ejecuta UN ciclo de monitoreo de routers y APs.
    Esta función es llamada periódicamente por APScheduler.
    Wraps the async implementation.
    """
    # 1. Get configuration synchronously (keeps it simple/safe)
    session_sync = next(get_sync_session())
    max_workers = 10
    try:
        settings_service = SettingsService(session_sync)
        all_settings = settings_service.get_all_settings()
        max_workers_str = all_settings.get("monitor_max_workers")
        try:
            max_workers = int(max_workers_str) if max_workers_str else 10
        except (ValueError, TypeError):
            logger.warning(
                f"Valor inválido para monitor_max_workers: {max_workers_str}. Usando default: 10"
            )
    finally:
        session_sync.close()

    # 2. Run Async Cycle
    try:
        asyncio.run(run_monitor_cycle_async(max_workers))
    except Exception as e:
        logger.exception(f"Error en el ciclo del monitor: {e}")


async def run_monitor_cycle_async(max_workers: int):
    monitor_service = MonitorService()
    logger.info(f"--- Iniciando ciclo de escaneo (concurrency: {max_workers}) ---")

    async with async_session_maker() as session:
        devices = await monitor_service.get_active_devices(session)
        aps = devices["aps"]
        routers = devices["routers"]

        all_tasks = []
        # Create a semaphore to limit concurrency equivalent to max_workers
        sem = asyncio.Semaphore(max_workers)

        async def sem_check_ap(ap_obj):
            async with sem:
                await monitor_service.check_ap(session, ap_obj)

        async def sem_check_router(router_obj):
            async with sem:
                await monitor_service.check_router(session, router_obj)

        if not aps and not routers:
            logger.info("No hay dispositivos para monitorear.")
        else:
            if aps:
                for ap in aps:
                    all_tasks.append(sem_check_ap(ap))
            
            if routers:
                for router in routers:
                    all_tasks.append(sem_check_router(router))

            if all_tasks:
                await asyncio.gather(*all_tasks)

            # Notificar a la API
            logger.info(
                "Ciclo terminado. Notificando a la API para actualización en tiempo real..."
            )
            # notify uses synchronous httpx? or fire and forget?
            # It's a network call. Let's make it async or run in thread.
            # notify_api_update is currently sync using httpx.post (blocking).
            await asyncio.to_thread(notify_api_update)

            logger.info("--- Ciclo de escaneo completado ---")
