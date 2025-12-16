# app/api/aps/main.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
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
    """
    Registra un nuevo Access Point en el sistema.
    Valida que la IP/Host no esté duplicada.
    """
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
    """
    Obtiene la lista completa de APs registrados.
    """
    aps_data = await service.get_all_aps()
    return [AP(**ap) for ap in aps_data]


@router.get("/aps/{host}", response_model=AP)
async def get_ap(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene detalles de un AP específico por su Host/IP.
    """
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
    """
    Actualiza la configuración de un AP existente.
    Si se cambia la IP, se actualizan también sus referencias.
    """
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
    request: Request,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Elimina un AP del sistema y registra la acción en auditoría.
    """
    from ...core.audit import log_action
    try:
        await service.delete_ap(host)
        log_action("DELETE", "ap", host, user=current_user, request=request)
        return
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/aps/{host}/cpes", response_model=List[CPEDetail])
def get_cpes_for_ap(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Lista todos los CPEs (clientes) conectados a este AP.
    """
    cpes_data = service.get_cpes_for_ap(host)
    return [CPEDetail(**cpe) for cpe in cpes_data]


@router.get("/aps/{host}/live", response_model=APLiveDetail)
async def get_ap_live_data(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene métricas en tiempo real (CPU, RAM, uso de frecuencias) conectando directamente al dispositivo.
    """
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
    """
    Obtiene historial de métricas (tráfico, señal, clientes conectados) para gráficos.
    Periodos soportados: '24h', '7d', '30d'.
    """
    try:
        return await service.get_ap_history(host, period)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APDataError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aps/{host}/wireless-interfaces")
async def get_wireless_interfaces(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene las interfaces inalámbricas disponibles en un AP MikroTik.
    Para usar con Spectral Scan.
    """
    try:
        interfaces = await service.get_wireless_interfaces(host)
        return {"interfaces": interfaces}
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/aps/validate", status_code=200)
def validate_ap_connection(ap_data: APCreate):
    """
    Intenta conectar con el AP usando las credenciales proporcionadas.
    No guarda nada en la BD. Retorna éxito o error.
    Soporta múltiples vendors (ubiquiti, mikrotik).
    """
    from ...utils.device_clients.adapter_factory import get_device_adapter

    adapter = None
    try:
        # Use adapter factory to get the appropriate adapter for the vendor
        adapter = get_device_adapter(
            host=ap_data.host,
            username=ap_data.username,
            password=ap_data.password,
            vendor=ap_data.vendor,
            port=ap_data.api_port,
        )

        # Get device status to validate connection
        status = adapter.get_status()

        if status.is_online:
            # Extract basic info to confirm to the user
            hostname = status.hostname or "Unknown"
            model = status.model or "Unknown"
            vendor_display = ap_data.vendor.capitalize()

            return {
                "status": "success",
                "message": f"Conexión Exitosa ({vendor_display}): {hostname} ({model})",
            }
        else:
            # Device offline or connection failed
            error_msg = status.last_error or "No se pudo obtener datos del dispositivo"
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo conectar: {error_msg}",
            )

    except ValueError as e:
        # Unsupported vendor
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Catch any unhandled connection errors
        raise HTTPException(status_code=400, detail=f"Error de conexión: {str(e)}")
    finally:
        # Always cleanup the adapter connection
        if adapter:
            adapter.disconnect()
