# app/api/cpes/main.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ...core.users import require_technician
from ...db.engine_sync import get_sync_session
from ...models.user import User
from ...services.cpe_service import CPEService
from .models import AssignedCPE, CPEGlobalInfo, CPEUpdate

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
def get_cpe_service(session: Session = Depends(get_sync_session)) -> CPEService:
    return CPEService(session)


# --- Endpoints de la API ---
@router.get("/cpes/unassigned", response_model=list[AssignedCPE])
def api_get_unassigned_cpes(
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    return service.get_unassigned_cpes()


@router.post("/cpes/{mac}/assign/{client_id}", response_model=AssignedCPE)
def api_assign_cpe_to_client(
    mac: str,
    client_id: uuid.UUID,
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    try:
        return service.assign_cpe_to_client(mac, client_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cpes/{mac}/unassign", response_model=AssignedCPE)
def api_unassign_cpe(
    mac: str,
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    try:
        return service.unassign_cpe(mac)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cpes/{mac}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_cpe(
    mac: str,
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    """Elimina un CPE de la base de datos de forma permanente."""
    try:
        service.delete_cpe(mac)
        return None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cpes/{mac}", response_model=AssignedCPE)
def api_update_cpe(
    mac: str,
    update_data: CPEUpdate,
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    """Update CPE properties (IP address, hostname, model)."""
    try:
        return service.update_cpe(mac, update_data.model_dump(exclude_none=True))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cpes/all", response_model=list[CPEGlobalInfo])
def api_get_all_cpes_globally(
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status: 'active', 'offline', 'disabled'"
    ),
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    """Get all CPEs globally with status (active/fallen/disabled)."""
    try:
        return service.get_all_cpes_globally(status_filter=status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
