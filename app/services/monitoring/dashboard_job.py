# app/services/monitoring/dashboard_job.py
import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.utils.cache import cache_manager
from app.api.stats.main import compute_dashboard_summary_from_db
from app.models.user import User

logger = logging.getLogger("DashboardJob")


def run_dashboard_cache_job():
    """
    Ejecuta un ciclo de pre-cálculo para la caché del Dashboard.
    Esta función es llamada periódicamente por APScheduler.
    Wraps the async implementation.
    """
    try:
        asyncio.run(run_dashboard_cache_job_async())
    except Exception as e:
        logger.exception(f"Error en el job de caché de dashboard: {e}")


async def run_dashboard_cache_job_async():
    """
    Ciclo de actualización de caché del Dashboard completamente aislado.
    Crea su propio engine/pool async para no interferir con el de FastAPI.
    """
    _db_url = settings.DATABASE_URL
    _is_sqlite = _db_url.startswith("sqlite")

    if _is_sqlite:
        from sqlalchemy.pool import NullPool
        _engine = create_async_engine(_db_url, echo=False, poolclass=NullPool)
    else:
        _engine = create_async_engine(
            _db_url,
            echo=False,
            pool_size=2,
            max_overflow=0,
        )

    _session_maker = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        logger.info("--- Iniciando ciclo de pre-cálculo de caché de Dashboard ---")
        
        async with _session_maker() as session:
            # Obtener el primer administrador para calcular las estadísticas globales
            from sqlmodel import select
            user_stmt = select(User).where(User.is_superuser == True).limit(1)
            user_result = await session.exec(user_stmt)
            admin_user = user_result.first()
            
            if not admin_user:
                # Fallback: buscar cualquier usuario activo
                user_stmt = select(User).where(User.is_active == True).limit(1)
                user_result = await session.exec(user_stmt)
                admin_user = user_result.first()
                
            if not admin_user:
                logger.warning("No se encontró ningún usuario para calcular estadísticas del dashboard.")
                return

            # Calcular resumen de estadísticas secuencialmente con eager loading
            payload = await compute_dashboard_summary_from_db(session, admin_user)

            # Guardar en caché con TTL de 60 segundos
            stats_cache = cache_manager.get_store("dashboard_stats")
            await stats_cache.set_async("summary", payload, ttl=60)
            
            logger.info("✅ Caché del resumen del Dashboard actualizada exitosamente")
    finally:
        # Siempre cerrar el engine local para liberar conexiones
        await _engine.dispose()
