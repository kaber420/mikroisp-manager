# app/api/cpes/main.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlmodel import Session

from ...core.users import require_technician
from ...models.user import User
from ...db.engine_sync import get_sync_session
from ...services.cpe_service import CPEService
from .models import CPEGlobalInfo, AssignedCPE

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
def get_cpe_service(session: Session = Depends(get_sync_session)) -> CPEService:
    return CPEService(session)



# --- Endpoints de la API ---
@router.get("/cpes/unassigned", response_model=List[AssignedCPE])
def api_get_unassigned_cpes(
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    return service.get_unassigned_cpes()


@router.post("/cpes/{mac}/assign/{client_id}", response_model=AssignedCPE)
def api_assign_cpe_to_client(
    mac: str,
    client_id: int,
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


@router.get("/cpes/all", response_model=List[CPEGlobalInfo])
def api_get_all_cpes_globally(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: 'active', 'offline', 'disabled'"
    ),
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(require_technician),
):
    """Get all CPEs globally with status (active/fallen/disabled)."""
    try:
        return service.get_all_cpes_globally(status_filter=status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
