from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from app.core.security import require_admin
from ...db.engine import get_session
from ...db.engine_sync import get_sync_session
from ...models.user import User
from ...services.business.billing_service import BillingService
from ...services.core.settings_service import SettingsService
from .models import SystemSettingsRequest

from .preferences import router as preferences_router
from .infra import router as infra_router

router = APIRouter()
router.include_router(preferences_router, prefix="/preferences", tags=["Preferences"])
router.include_router(infra_router, prefix="/infra", tags=["Infrastructure"])


async def get_settings_service(
    session: AsyncSession = Depends(get_session),
) -> SettingsService:
    return SettingsService(session)


@router.get("/settings", response_model=dict[str, str])
async def api_get_settings(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_admin),
):
    return await service.get_all_settings()


@router.get("/settings/public", response_model=dict[str, str])
async def api_get_public_settings(
    service: SettingsService = Depends(get_settings_service),
):
    """
    Returns public settings safe for unauthenticated or basic users.
    """
    settings = await service.get_all_settings()
    public_keys = [
        "company_name", 
        "company_logo_url", 
        "ticket_footer_message", 
        "billing_address",
        "cpe_signal_warning_threshold",
        "cpe_signal_danger_threshold",
        "client_bot_username"
    ]
    return {k: v for k, v in settings.items() if k in public_keys}


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
async def api_update_settings(
    settings: dict[str, str],
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_admin),
):
    await service.update_settings(settings)
    return



from ...utils.services_config import read_services_config, write_services_config
from ...utils.service_probe import test_postgres_connection, test_sqlite_connection, test_redict_connection, test_memory_cache_connection
from ...core.config import settings
import re
from pydantic import BaseModel
from typing import Optional

class ServiceTestRequest(BaseModel):
    provider: str # postgres, sqlite, redict, memory
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    user: Optional[str] = ""
    password: Optional[str] = ""
    database: Optional[str] = ""

@router.get("/settings/system/services")
async def api_get_services_config(current_user: User = Depends(require_admin)):
    """
    Lee la configuración de servicios desde data/services.json
    """
    return read_services_config()

@router.post("/settings/system/services")
async def api_save_services_config(config: dict, current_user: User = Depends(require_admin)):
    """
    Guarda la configuración de servicios en data/services.json.
    """
    try:
        write_services_config(config)
        return {"message": "Configuración guardada. Los cambios se aplicarán en el próximo reinicio."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/system/test-connection")
async def api_test_service_connection(req: ServiceTestRequest, current_user: User = Depends(require_admin)):
    if req.provider == "postgres":
        return test_postgres_connection(req.host, req.port or 5432, req.user or "umanager", req.password or "", req.database or "umanager_db")
    elif req.provider == "sqlite":
        return test_sqlite_connection()
    elif req.provider == "redict":
        return test_redict_connection(req.host, req.port or 6379, req.password or "", int(req.database or 0))
    elif req.provider == "memory":
        return test_memory_cache_connection()
    raise HTTPException(status_code=400, detail="Provider no soportado")

@router.get("/settings/system/status")
async def api_get_system_status(current_user: User = Depends(require_admin)):
    """
    Devuelve el estado de los servicios actuales y si están respondiendo.
    """
    # 1. Database
    db_backend = "sqlite" if settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite") else "postgres"
    if settings.DATABASE_URL is None: 
        db_backend = "sqlite" 
    
    db_online = True
    if db_backend == "postgres" and settings.DATABASE_URL_SYNC:
        m = re.match(r"postgresql\+psycopg://(.*?):(.*?)@(.*?):(\d+)/(.*)", settings.DATABASE_URL_SYNC)
        if m:
            res = test_postgres_connection(m.group(3), int(m.group(4)), m.group(1), m.group(2), m.group(5))
            db_online = res["ok"]
        else:
            db_online = False
    else:
        db_online = test_sqlite_connection()["ok"]

    # 2. Caché
    cache_backend = settings.CACHE_BACKEND
    cache_online = True
    if cache_backend == "redict" and settings.REDICT_URL:
        m = re.match(r"redis://(:(.*?)@)?(.*?):(\d+)/(.*)", settings.REDICT_URL)
        if m:
            pwd = m.group(2) if m.group(2) else ""
            res = test_redict_connection(m.group(3), int(m.group(4)), pwd, int(m.group(5)))
            cache_online = res["ok"]
        else:
            cache_online = False
            
    mode = "degraded" if settings.DEGRADED_MODE else "normal"
    
    # Hide passwords from URLs for the UI
    db_url_safe = re.sub(r":([^:@]+)@", ":***@", settings.DATABASE_URL_SYNC) if settings.DATABASE_URL_SYNC else "sqlite:///"
    cache_url_safe = re.sub(r":([^:@]+)@", ":***@", settings.REDICT_URL) if settings.REDICT_URL else ""
    
    return {
        "mode": mode,
        "is_forced_sqlite": settings.IS_FORCED_SQLITE,
        "db": {
            "backend": db_backend,
            "url": db_url_safe,
            "online": db_online
        },
        "cache": {
            "backend": cache_backend,
            "url": cache_url_safe,
            "online": cache_online
        }
    }

# --- NUEVOS ENDPOINTS DE GESTIÓN MANUAL ---



@router.post("/settings/force-billing", status_code=200)
def force_billing_update(
    session: Session = Depends(get_sync_session), current_user: User = Depends(require_admin)
):
    """
    Endpoint administrativo para forzar la actualización de estados de facturación.
    """
    try:
        service = BillingService(session)
        stats = service.process_daily_suspensions()
        return {"message": "Estados actualizados correctamente.", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/force-monitor", status_code=200)
def force_monitor_scan(current_user: User = Depends(require_admin)):
    """
    Dispara una señal (simulada o real) para el monitor.
    Nota: En esta arquitectura simple, esto solo devuelve confirmación ya que el monitor corre en otro proceso.
    Para una implementación real de 'forzar ahora', se requeriría una cola de tareas compartida (Redis/Celery).
    """
    return {"message": "El monitor continuará su ciclo en segundo plano (intervalo normal)."}


@router.post("/settings/restart-bots", status_code=200)
async def restart_bots(current_user: User = Depends(require_admin)):
    """
    Reinicia el subsistema de bots (BotManager).
    Útil después de cambiar tokens o modo de ejecución (Polling/Webhook).
    """
    from ...services.core.bot_manager import bot_manager
    await bot_manager.stop()
    await bot_manager.start()
    return {"message": "Bots reiniciados correctamente."}


# --- AUDIT LOGS ENDPOINTS (Admin Only) ---

# --- AUDIT LOGS ENDPOINTS (Admin Only) ---

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.engine import get_session
from ...services.core.audit_service import AuditService


async def get_audit_service(
    session: AsyncSession = Depends(get_session),
) -> AuditService:
    return AuditService(session)


@router.get("/settings/audit-logs")
async def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str = None,
    username: str = None,
    service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_admin),
):
    """
    Retrieves paginated audit logs for admin review.
    Supports filtering by action type and username.
    """
    logs = await service.get_audit_logs_paginated(page, page_size, action, username)
    total_records = await service.count_audit_logs(action, username)
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return {
        "items": logs,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/settings/audit-logs/filters")
async def get_audit_log_filters(
    service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_admin),
):
    """
    Returns available filter options for audit logs.
    """
    return {
        "actions": await service.get_distinct_actions(),
        "usernames": await service.get_distinct_usernames(),
    }


# --- DATABASE BACKUP ENDPOINT ---
import os
import subprocess

from fastapi import Request

from ...core.audit import log_action


@router.post("/settings/backup-now", status_code=200)
def trigger_manual_backup(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """
    Triggers a manual database backup using the db_backup.sh script.
    """
    # Construct path to the backup script relative to this file
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "scripts", "db_backup.sh"
    )
    script_path = os.path.abspath(script_path)

    if not os.path.exists(script_path):
        log_action(
            action="BACKUP",
            resource_type="database",
            resource_id="inventory.sqlite",
            user=current_user,
            request=request,
            status="failure",
            details={"error": "Backup script not found"},
        )
        raise HTTPException(status_code=500, detail="Backup script not found on server.")

    try:
        result = subprocess.run(
            ["bash", script_path, "manual"],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
        if result.returncode == 0:
            log_action(
                action="BACKUP",
                resource_type="database",
                resource_id="inventory.sqlite",
                user=current_user,
                request=request,
                status="success",
            )
            return {"message": "Backup completed successfully.", "output": result.stdout}
        else:
            log_action(
                action="BACKUP",
                resource_type="database",
                resource_id="inventory.sqlite",
                user=current_user,
                request=request,
                status="failure",
                details={"error": result.stderr},
            )
            raise HTTPException(status_code=500, detail=f"Backup failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        log_action(
            action="BACKUP",
            resource_type="database",
            resource_id="inventory.sqlite",
            user=current_user,
            request=request,
            status="failure",
            details={"error": "Backup script timed out"},
        )
        raise HTTPException(status_code=500, detail="Backup script timed out.")
    except Exception as e:
        log_action(
            action="BACKUP",
            resource_type="database",
            resource_id="inventory.sqlite",
            user=current_user,
            request=request,
            status="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

