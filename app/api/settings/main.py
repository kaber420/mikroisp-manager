from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ...core.users import require_admin
from ...db.engine_sync import get_sync_session
from ...models.user import User
from ...services.billing_service import BillingService
from ...services.settings_service import SettingsService

router = APIRouter()


def get_settings_service(session: Session = Depends(get_sync_session)) -> SettingsService:
    return SettingsService(session)


@router.get("/settings", response_model=dict[str, str])
def api_get_settings(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_admin),
):
    return service.get_all_settings()


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def api_update_settings(
    settings: dict[str, str],
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_admin),
):
    service.update_settings(settings)
    return


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


# --- AUDIT LOGS ENDPOINTS (Admin Only) ---

from ...db.audit_db import (
    count_audit_logs,
    get_audit_logs_paginated,
    get_distinct_actions,
    get_distinct_usernames,
)


@router.get("/settings/audit-logs")
def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str = None,
    username: str = None,
    current_user: User = Depends(require_admin),
):
    """
    Retrieves paginated audit logs for admin review.
    Supports filtering by action type and username.
    """
    logs = get_audit_logs_paginated(page, page_size, action, username)
    total_records = count_audit_logs(action, username)
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return {
        "items": logs,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/settings/audit-logs/filters")
def get_audit_log_filters(
    current_user: User = Depends(require_admin),
):
    """
    Returns available filter options for audit logs.
    """
    return {
        "actions": get_distinct_actions(),
        "usernames": get_distinct_usernames(),
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

