# app/api/aps/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.engine import get_session

# --- RBAC: Use require_technician for all AP operations ---
from ...core.users import require_technician
from ...models.user import User
from ...services.ap_service import (
    APService,
    APNotFoundError,
    APUnreachableError,
    APDataError,
    APCreateError,
)

# --- ¡IMPORTACIÓN CORREGIDA! (Ahora desde '.models') ---
from .models import (
    AP,
    APCreate,
    APUpdate,
    CPEDetail,
    APLiveDetail,
    HistoryDataPoint,
    APHistoryResponse,
)

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
async def get_ap_service(session: AsyncSession = Depends(get_session)) -> APService:
    return APService(session)


# --- Endpoints de la API (Sin cambios en la lógica) ---


@router.post("/aps", response_model=AP, status_code=status.HTTP_201_CREATED)
async def create_ap(
    ap: APCreate,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        new_ap_data = await service.create_ap(ap)
        return AP(**new_ap_data)
    except APCreateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@router.get("/aps", response_model=List[AP])
async def get_all_aps(
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    aps_data = await service.get_all_aps()
    return [AP(**ap) for ap in aps_data]


@router.get("/aps/{host}", response_model=AP)
async def get_ap(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        ap_data = await service.get_ap_by_host(host)
        return AP(**ap_data)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/aps/{host}", response_model=AP)
async def update_ap(
    host: str,
    ap_update: APUpdate,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        updated_ap_data = await service.update_ap(host, ap_update)
        return AP(**updated_ap_data)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APDataError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/aps/{host}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ap(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        await service.delete_ap(host)
        return
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/aps/{host}/cpes", response_model=List[CPEDetail])
def get_cpes_for_ap(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    cpes_data = service.get_cpes_for_ap(host)
    return [CPEDetail(**cpe) for cpe in cpes_data]


@router.get("/aps/{host}/live", response_model=APLiveDetail)
async def get_ap_live_data(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        return await service.get_live_data(host)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/aps/{host}/history", response_model=APHistoryResponse)
async def get_ap_history(
    host: str,
    period: str = "24h",
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    try:
        return await service.get_ap_history(host, period)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APDataError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aps/validate", status_code=200)
def validate_ap_connection(ap_data: APCreate):
    """
    Intenta conectar con el AP usando las credenciales proporcionadas.
    No guarda nada en la BD. Retorna éxito o error.
    """
    # Importación local para usar el proveedor de clientes
    from ...utils.device_clients.client_provider import (
        get_ubiquiti_client,
        remove_ubiquiti_client,
    )

    try:
        # Usamos el proveedor para obtener un cliente.
        client = get_ubiquiti_client(
            host=ap_data.host,
            username=ap_data.username,
            password=ap_data.password,
            port=ap_data.port,
            http_mode=ap_data.http_mode,
        )

        # Intentamos obtener datos. Si falla la autenticación o conexión, get_status_data suele retornar None.
        status_data = client.get_status_data()

        if status_data:
            # Extraemos info básica para confirmar al usuario
            hostname = status_data.get("host", {}).get("hostname", "Unknown")
            model = status_data.get("host", {}).get("devmodel", "Unknown")

            # Importante: Como esta es una validación, no queremos dejar la sesión
            # en la caché si la configuración del AP no se guarda.
            # La eliminamos explícitamente.
            remove_ubiquiti_client(ap_data.host)

            return {
                "status": "success",
                "message": f"Conexión Exitosa: {hostname} ({model})",
            }
        else:
            # Si get_status_data retorna None (fallo auth/red manejado internamente)
            raise HTTPException(
                status_code=400,
                detail="No se pudo conectar. Verifique IP/Credenciales o que el dispositivo esté online.",
            )

    except Exception as e:
        # Captura cualquier error de conexión no manejado
        raise HTTPException(status_code=400, detail=f"Error de conexión: {str(e)}")
