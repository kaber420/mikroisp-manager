# app/api/aps/main.py
"""
AP (Access Point) API endpoints.

This module has been refactored for maintainability:
- CRUD operations remain here
- WebSocket streaming moved to ws.py
- Provisioning/repair moved to provisioning.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.audit import log_action
from ...core.users import require_admin, require_technician
from ...db.engine import async_session_maker, get_session
from ...models.user import User
from ...services.ap_service import (
    APCreateError,
    APDataError,
    APNotFoundError,
    APService,
    APUnreachableError,
)

from .dependencies import get_ap_service
from .models import (
    AP,
    APCreate,
    APHistoryResponse,
    APLiveDetail,
    APUpdate,
    CPEDetail,
)

# Import sub-routers
from . import provisioning as provisioning_api
from . import ws as ws_api

router = APIRouter()

# Include sub-routers
router.include_router(ws_api.router)
router.include_router(provisioning_api.router)


# --- CRUD Endpoints ---


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


@router.get("/aps", response_model=list[AP])
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
    try:
        await service.delete_ap(host)
        log_action("DELETE", "ap", host, user=current_user, request=request)
        return
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Specialized Endpoints ---


@router.post("/aps/{host}/sync-names")
async def sync_cpe_names(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Synchronizes CPE hostnames by fetching ARP table from the AP.
    Updates the CPE inventory database with resolved hostnames.
    
    This is a 'heavy' operation intended to be triggered manually via a button,
    not during every live poll.
    """
    try:
        result = await service.sync_cpe_names(host)
        return result
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/aps/{host}/cpes", response_model=list[CPEDetail])
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


@router.get("/aps/{host}/ssl/status")
async def get_ap_ssl_status(
    host: str,
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene el estado SSL/TLS de un AP MikroTik.
    Retorna si SSL está habilitado, si el certificado es confiable, etc.
    """
    from ...models.ap import AP as APModel
    from ...utils.device_clients.adapter_factory import get_device_adapter
    from ...utils.security import decrypt_data

    # Get AP from database
    async with async_session_maker() as session:
        ap = await session.get(APModel, host)
        if not ap:
            raise HTTPException(status_code=404, detail=f"AP {host} not found")

        # Only MikroTik APs support SSL status check
        if ap.vendor != "mikrotik":
            return {
                "ssl_enabled": False,
                "is_trusted": False,
                "status": "not_applicable",
                "message": f"SSL status only available for MikroTik devices. This AP is: {ap.vendor}",
            }

        vendor = ap.vendor
        username = ap.username
        password = decrypt_data(ap.password)
        port = ap.api_port or 8729

    adapter = None
    try:
        # Get adapter (MikrotikWirelessAdapter inherits get_ssl_status from MikrotikRouterAdapter)
        adapter = get_device_adapter(
            host=host,
            username=username,
            password=password,
            vendor=vendor,
            port=port,
        )

        # Call inherited method from MikrotikRouterAdapter (if available)
        if hasattr(adapter, "get_ssl_status"):
            status_data = adapter.get_ssl_status()
            return status_data
        else:
            return {"status": "not_supported", "message": "This adapter does not support SSL status"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking SSL status: {e}")
    finally:
        if adapter:
            adapter.disconnect()


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
    except APUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))


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
