# app/scheduler.py
import logging
import time

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .utils.settings_utils import get_setting_sync

logger = logging.getLogger("Scheduler")



def job_listener(event):
    """
    Listener para eventos del scheduler.
    Permite logging detallado de la ejecución de jobs.
    """
    if event.exception:
        logger.error(f"Job {event.job_id} falló: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} ejecutado exitosamente")


def run_scheduler(log_queue=None):
    """
    Punto de entrada para el proceso del scheduler.
    Configura y arranca todos los jobs programados.
    """
    # Configurar logging si viene la cola
    if log_queue:
        from launcher.log_queue import configure_process_logging
        configure_process_logging(log_queue)
    else:
        # Fallback para ejecución manual fuera de launcher
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [Scheduler] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Importaciones tardías para evitar problemas de circularidad
    from .services.billing_job import run_billing_check
    from .services.monitor_job import run_monitor_cycle

    logger.info("Inicializando BackgroundScheduler...")

    scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,  # Si se perdieron ejecuciones, solo ejecuta una vez
            "max_instances": 1,  # Solo una instancia del mismo job a la vez
            "misfire_grace_time": 300,  # Tolerar 5 min de retraso
        }
    )

    # Agregar listener para eventos
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # --- Job 1: Monitor de Routers/APs ---
    # Obtener intervalo desde la configuración
    interval_str = get_setting_sync("default_monitor_interval")
    try:
        monitor_interval = int(interval_str) if interval_str and interval_str.isdigit() else 300
    except (ValueError, TypeError):
        monitor_interval = 300

    logger.info(f"Programando Monitor cada {monitor_interval} segundos")
    scheduler.add_job(
        run_monitor_cycle,
        trigger=IntervalTrigger(seconds=monitor_interval),
        id="monitor_job",
        name="Router/AP Monitor",
        replace_existing=True,
    )

    # --- Job 2: Billing Engine (Suspensiones diarias) ---
    # Obtener hora desde la configuración
    run_hour_str = get_setting_sync("suspension_run_hour") or "02:00"
    try:
        hour, minute = run_hour_str.split(":")
        hour = int(hour)
        minute = int(minute)
    except (ValueError, AttributeError):
        logger.warning(f"Formato de hora inválido: {run_hour_str}. Usando 02:00")
        hour, minute = 2, 0

    logger.info(f"Programando Billing Check diario a las {hour:02d}:{minute:02d}")
    scheduler.add_job(
        run_billing_check,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="billing_job",
        name="Daily Billing Check",
        replace_existing=True,
    )

    # --- Job 3: Respaldo de Routers (Diario/Semanal) ---
    from .services.backup_service import run_backup_cycle

    # Obtener configuración de respaldo
    backup_frequency = get_setting_sync("backup_frequency") or "daily"
    backup_day_of_week = get_setting_sync("backup_day_of_week") or "mon"
    backup_run_hour = get_setting_sync("backup_run_hour") or "03:00"

    # Debug: mostrar valores leídos
    logger.info(f"   [DEBUG] backup_frequency = '{backup_frequency}'")
    logger.info(f"   [DEBUG] backup_day_of_week = '{backup_day_of_week}'")
    logger.info(f"   [DEBUG] backup_run_hour = '{backup_run_hour}'")

    try:
        b_hour, b_minute = backup_run_hour.split(":")
        b_hour = int(b_hour)
        b_minute = int(b_minute)
    except (ValueError, AttributeError):
        b_hour, b_minute = 3, 0

    # Configurar trigger según frecuencia
    if backup_frequency == "weekly":
        backup_trigger = CronTrigger(day_of_week=backup_day_of_week, hour=b_hour, minute=b_minute)
        logger.info(
            f"Programando Respaldo Semanal: {backup_day_of_week.upper()} a las {b_hour:02d}:{b_minute:02d}"
        )
    else:
        backup_trigger = CronTrigger(hour=b_hour, minute=b_minute)
        logger.info(f"Programando Respaldo Diario a las {b_hour:02d}:{b_minute:02d}")

    scheduler.add_job(
        run_backup_cycle,
        trigger=backup_trigger,
        id="backup_job",
        name="Router Backup",
        replace_existing=True,
    )

    # --- Job 4: Respaldo de Base de Datos (Diario) ---
    from .services.db_backup_service import run_db_backup
    
    db_backup_hour = get_setting_sync("db_backup_run_hour") or "04:00"
    try:
        db_h, db_m = db_backup_hour.split(":")
        db_h = int(db_h)
        db_m = int(db_m)
    except Exception:
        db_h, db_m = 4, 0
        
    logger.info(f"Programando Respaldo de BD Diario a las {db_h:02d}:{db_m:02d}")
    scheduler.add_job(
        run_db_backup,
        trigger=CronTrigger(hour=db_h, minute=db_m),
        id="db_backup_job",
        name="Database Backup",
        replace_existing=True,
    )

    # Iniciar el scheduler
    scheduler.start()
    logger.info("✅ Scheduler iniciado exitosamente")
    logger.info(f"   - Monitor: cada {monitor_interval}s")
    logger.info(f"   - Billing: diario a las {hour:02d}:{minute:02d}")

    # Mantener el proceso vivo
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Deteniendo scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler detenido")
