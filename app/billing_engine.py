# app/billing_engine.py
import time
import logging
from datetime import datetime

# --- Imports moved to top-level ---
from sqlmodel import Session
from .db.engine_sync import sync_engine
from .db import settings_db # Legacy settings access
from .services.billing_service import BillingService
from .services.router_service import RouterService, get_enabled_routers_sync, RouterConnectionError

# Configuración del Logger
logger = logging.getLogger("BillingEngine")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - [BillingEngine] - %(message)s")
    )
    logger.addHandler(handler)


def run_billing_engine():
    """
    Orquestador que ejecuta las suspensiones diarias utilizando BillingService.
    """
    logger.info("Motor de Facturación iniciado (Refactorizado).")
    last_run_date = None

    while True:
        try:
            # --- SESSION CONTEXT WRAPS THE ENTIRE LOGIC BLOCK ---
            with Session(sync_engine) as session:
                run_hour_str = settings_db.get_setting("suspension_run_hour") or "02:00"
                now = datetime.now()
                current_date = now.date()

                try:
                    run_time_today = datetime.strptime(
                        f"{current_date} {run_hour_str}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    logger.error(
                        f"Formato de hora inválido en configuración: {run_hour_str}. Usando 02:00."
                    )
                    run_time_today = datetime.strptime(
                        f"{current_date} 02:00", "%Y-%m-%d %H:%M"
                    )

                if now >= run_time_today and current_date != last_run_date:
                    logger.info(f"--- EJECUTANDO AUDITORÍA DE ESTADOS ({current_date}) ---")

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
                                        logger.info(f"   - Limpiadas {cleaned_count} conexiones en {router_creds.host}")
                            except RouterConnectionError as e:
                                logger.warning(f"   - No se pudo conectar a {router_creds.host} para limpiar: {e}")
                            except Exception as e:
                                logger.error(f"   - Error inesperado limpiando {router_creds.host}: {e}")
                    except Exception as e:
                        logger.error(f"Error crítico en la fase de limpieza de routers: {e}")

                    # --- 2. PROCESO DE FACTURACIÓN ---
                    billing_service = BillingService(session)
                    stats = billing_service.process_daily_suspensions()
                    logger.info(f"--- FIN DEL PROCESO. Resumen: {stats} ---")

                    last_run_date = current_date

            # Sleep outside the session context
            time.sleep(1800)

        except KeyboardInterrupt:
            logger.info("Motor detenido manualmente.")
            break
        except Exception as e:
            logger.critical(
                f"Error crítico en el bucle principal del motor de facturación: {e}", exc_info=True
            )
            # Wait longer after a critical failure
            time.sleep(60)
