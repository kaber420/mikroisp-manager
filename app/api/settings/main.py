from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from ...core.users import require_admin
from ...db.engine import get_session
from ...db.engine_sync import get_sync_session
from ...models.user import User
from ...services.billing_service import BillingService
from ...services.settings_service import SettingsService
from ...utils.env_manager import update_env_file, get_env_context
from .models import SystemSettingsRequest

router = APIRouter()


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


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
async def api_update_settings(
    settings: dict[str, str],
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_admin),
):
    await service.update_settings(settings)
    return



@router.get("/settings/system", response_model=dict[str, str])
async def api_get_system_settings(
    current_user: User = Depends(require_admin),
):
    """
    Returns current system configuration from .env context.
    """
    return get_env_context()

@router.post("/settings/system", status_code=status.HTTP_200_OK)
async def api_update_system_settings(
    config: SystemSettingsRequest,
    current_user: User = Depends(require_admin),
):
    """
    Updates system configuration (DB & Cache) in .env file.
    """
    updates = {}
    
    # 1. Database Configuration
    if config.db_provider == "postgres":
        # Construct SQLAlchemy URL: postgresql+psycopg://user:pass@host:port/db
        db_url = f"postgresql+psycopg://{config.postgres_user}:{config.postgres_password}@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
        updates["DATABASE_URL_SYNC"] = db_url
    else:
        # Revert to SQLite (remove var or set to default? removing is safer to fallback logic)
        # But here we explicitly set connection string if needed, or better, we can just remove the var.
        # However, our env_manager updates keys. Let's set it to sqlite explicitly if that's the logic.
        # The engine_sync.py logic checks if DATABASE_URL_SYNC starts with sqlite or is None.
        # So we can set it to a default sqlite path or empty to trigger default.
        # Ideally, we should just remove it to use default, but env_manager updates values.
        # Let's simple set it to sqlite:///data/db/inventory.sqlite to be explicit.
        updates["DATABASE_URL_SYNC"] = "sqlite:///data/db/inventory.sqlite"

    # 2. Cache Configuration
    if config.cache_provider == "redict":
        updates["CACHE_BACKEND"] = "redict"
        if config.redict_url:
            updates["REDICT_URL"] = config.redict_url
    else:
        updates["CACHE_BACKEND"] = "memory"
        # We don't remove REDICT_URL, just ignore it if backend is memory

    # 3. Apply Updates
    try:
        update_env_file(updates)
        return {"message": "Configuration updated. Please restart the system."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


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
    from ...services.bot_manager import bot_manager
    await bot_manager.stop()
    await bot_manager.start()
    return {"message": "Bots reiniciados correctamente."}


# --- AUDIT LOGS ENDPOINTS (Admin Only) ---

# --- AUDIT LOGS ENDPOINTS (Admin Only) ---

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.engine import get_session
from ...services.audit_service import AuditService


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

