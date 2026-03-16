
import asyncio
import logging

import httpx
from app.core.config import settings


# Configuración del logging
logger = logging.getLogger("MonitorJob")


def notify_api_update():
    """
    Envía una señal HTTP a la API para que actualice los WebSockets.
    Se ejecuta al finalizar cada ciclo de escaneo.
    """
    try:
        port = settings.UVICORN_PORT
        url = f"http://127.0.0.1:{port}/api/internal/notify-monitor-update"
        httpx.post(url, timeout=2)
    except Exception:
        pass


def run_monitor_cycle():
    """
    Ejecuta UN ciclo de monitoreo de routers y APs.
    Esta función es llamada periódicamente por APScheduler.
    Wraps the async implementation.
    """
    from app.utils.settings_utils import get_setting_sync

    max_workers = 10
    try:
        max_workers_str = get_setting_sync("monitor_max_workers")
        try:
            max_workers = int(max_workers_str) if max_workers_str else 10
        except (ValueError, TypeError):
            logger.warning(
                f"Valor inválido para monitor_max_workers: {max_workers_str}. Usando default: 10"
            )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")

    try:
        asyncio.run(run_monitor_cycle_async(max_workers))
    except Exception as e:
        logger.exception(f"Error en el ciclo del monitor: {e}")


async def run_monitor_cycle_async(max_workers: int):
    """
    Ciclo de monitoreo completamente aislado.
    Crea su propio engine/pool async para no interferir con el pool
    principal de FastAPI (evita 'another operation is in progress' de asyncpg).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from .monitor_service import MonitorService

    # --- Engine local al ciclo (aislado del pool de uvicorn) ---
    _db_url = settings.DATABASE_URL
    _is_sqlite = _db_url.startswith("sqlite")

    if _is_sqlite:
        # SQLite async no soporta pool_size; usamos NullPool
        from sqlalchemy.pool import NullPool
        _engine = create_async_engine(_db_url, echo=False, poolclass=NullPool)
    else:
        # PostgreSQL: pool propio dimensionado al número de workers
        _engine = create_async_engine(
            _db_url,
            echo=False,
            pool_size=max_workers + 2,
            max_overflow=0,
        )

    _session_maker = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        monitor_service = MonitorService()
        logger.info(f"--- Iniciando ciclo de escaneo (concurrency: {max_workers}) ---")

        devices = await monitor_service.get_active_devices_with_session(_session_maker)
        aps = devices["aps"]
        routers = devices["routers"]

        sem = asyncio.Semaphore(max_workers)

        async def sem_check_ap(ap_obj):
            async with sem:
                async with _session_maker() as session:
                    await monitor_service.check_ap(session, ap_obj)

        async def sem_check_router(router_obj):
            async with sem:
                async with _session_maker() as session:
                    await monitor_service.check_router(session, router_obj)

        if not aps and not routers:
            logger.info("No hay dispositivos para monitorear.")
        else:
            all_tasks = []
            if aps:
                for ap in aps:
                    all_tasks.append(sem_check_ap(ap))
            if routers:
                for router in routers:
                    all_tasks.append(sem_check_router(router))

            if all_tasks:
                await asyncio.gather(*all_tasks)

                logger.info(
                    "Ciclo terminado. Notificando a la API para actualización en tiempo real..."
                )
                await asyncio.to_thread(notify_api_update)
                logger.info("--- Ciclo de escaneo completado ---")
    finally:
        # Siempre cerrar el engine local para liberar conexiones del pool
        await _engine.dispose()
