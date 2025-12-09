# app/monitor.py
# ⚠️ DEPRECATED - Este módulo ha sido refactorizado
# 
# Este archivo se mantiene solo para compatibilidad temporal.
# 
# La funcionalidad de monitoreo ahora se ejecuta a través de APScheduler.
# 
# Archivos relevantes:
# - app/scheduler.py: Configuración del scheduler
# - app/services/monitor_job.py: Lógica de monitoreo extraída
# 
# Si necesitas ejecutar el monitor manualmente para pruebas:

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [Monitor] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def run_monitor():
    """
    ⚠️ DEPRECATED: Usar app.scheduler.run_scheduler() en su lugar.
    
    Esta función se mantiene solo para compatibilidad temporal.
    """
    logger.error("❌ ERROR: Este módulo está deprecado.")
    logger.error("   Por favor usa 'app.scheduler.run_scheduler()' en su lugar.")
    logger.error("   Ver 'app/services/monitor_job.py' para la nueva implementación.")
    
    import sys
    sys.exit(1)


# Para pruebas manuales del ciclo de monitoreo:
if __name__ == "__main__":
    from .services.monitor_job import run_monitor_cycle
    
    logger.info("🧪 Modo de prueba: Ejecutando un solo ciclo de monitoreo...")
    run_monitor_cycle()
    logger.info("✅ Ciclo completado")
