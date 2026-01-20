# app/services/billing_job.py
import logging

from sqlmodel import Session

from ..db.engine_sync import sync_engine
from .billing_service import BillingService
from .router_service import RouterConnectionError, RouterService, get_enabled_routers_sync

# Configuración del Logger
logger = logging.getLogger("BillingJob")


def run_billing_check():
    """
    Ejecuta UNA auditoría de facturación y suspensiones.
    Esta función es llamada diariamente por APScheduler.
    """
    logger.info("--- EJECUTANDO AUDITORÍA DE ESTADOS ---")

    try:
        # --- SESSION CONTEXT WRAPS THE ENTIRE LOGIC BLOCK ---
        with Session(sync_engine) as session:
            # --- 1. LIMPIEZA PREVIA DE ROUTERS ---
            try:
                routers = get_enabled_routers_sync(session)
                logger.info(
                    f"🧹 Saneando conexiones en {len(routers)} routers antes de facturar..."
                )
                for router_creds in routers:
                    try:
                        # Instantiate service with the full Router object
                        with RouterService(router_creds.host, router_creds) as rs:
                            cleaned_count = rs.cleanup_connections()
                            if cleaned_count > 0:
                                logger.info(
                                    f"   - Limpiadas {cleaned_count} conexiones en {router_creds.host}"
                                )
                    except RouterConnectionError as e:
                        logger.warning(
                            f"   - No se pudo conectar a {router_creds.host} para limpiar: {e}"
                        )
                    except Exception as e:
                        logger.error(f"   - Error inesperado limpiando {router_creds.host}: {e}")
            except Exception as e:
                logger.error(f"Error crítico en la fase de limpieza de routers: {e}")

            # --- 2. PROCESO DE FACTURACIÓN ---
            billing_service = BillingService(session)
            stats = billing_service.process_daily_suspensions()
            logger.info(f"--- FIN DEL PROCESO. Resumen: {stats} ---")

    except Exception as e:
        logger.critical(f"Error crítico en la auditoría de facturación: {e}", exc_info=True)
