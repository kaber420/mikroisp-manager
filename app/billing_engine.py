# app/billing_engine.py
# ⚠️ DEPRECATED - Este módulo ha sido refactorizado
# 
# Este archivo se mantiene solo para compatibilidad temporal.
# 
# La funcionalidad de facturación ahora se ejecuta a través de APScheduler.
# 
# Archivos relevantes:
# - app/scheduler.py: Configuración del scheduler
# - app/services/billing_job.py: Lógica de facturación extraída
# 
# Si necesitas ejecutar el billing manualmente para pruebas:

import logging

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
    ⚠️ DEPRECATED: Usar app.scheduler.run_scheduler() en su lugar.
    
    Esta función se mantiene solo para compatibilidad temporal.
    """
    logger.error("❌ ERROR: Este módulo está deprecado.")
    logger.error("   Por favor usa 'app.scheduler.run_scheduler()' en su lugar.")
    logger.error("   Ver 'app/services/billing_job.py' para la nueva implementación.")
    
    import sys
    sys.exit(1)


# Para pruebas manuales del proceso de facturación:
if __name__ == "__main__":
    from .services.billing_job import run_billing_check
    
    logger.info("🧪 Modo de prueba: Ejecutando una auditoría de facturación...")
    run_billing_check()
    logger.info("✅ Auditoría completada")
