# app/api/aps/main.py
import asyncio
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

# --- RBAC: Use require_technician for all AP operations ---
from ...core.users import require_admin, require_technician
from ...db import settings_db
from ...db.engine import async_session_maker, get_session
from ...models.user import User
from ...services.ap_service import (
    APCreateError,
    APDataError,
    APNotFoundError,
    APService,
    APUnreachableError,
)

# --- ¡IMPORTACIÓN CORREGIDA! (Ahora desde '.models') ---
from .models import (
    AP,
    APCreate,
    APHistoryResponse,
    APLiveDetail,
    APUpdate,
    CPEDetail,
)

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
async def get_ap_service(session: AsyncSession = Depends(get_session)) -> APService:
    return APService(session)


# --- Endpoints de la API (Sin cambios en la lógica) ---


# --- WebSocket Stream para Datos en Vivo (Patrón Scheduler + Cache) ---
@router.websocket("/ws/aps/{host}/resources")
async def ap_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del AP.

    ARQUITECTURA V2 (Scheduler + Cache compartido):
    - NO crea conexión directa al AP.
    - Se suscribe al APMonitorScheduler.
    - Lee del CacheManager local (compartido entre usuarios).
    """
    from ...models.ap import AP as APModel
    from ...services.ap_monitor_scheduler import ap_monitor_scheduler
    from ...utils.cache import cache_manager
    from ...utils.security import decrypt_data

    await websocket.accept()

    try:
        # 1. Get AP from DB and prepare credentials
        async with async_session_maker() as session:
            ap = await session.get(APModel, host)
            if not ap:
                await websocket.send_json(
                    {"type": "error", "data": {"message": f"AP {host} no encontrado"}}
                )
                await websocket.close()
                return

            # Copy needed data before session closes
            vendor = ap.vendor or "mikrotik"
            username = ap.username
            password = decrypt_data(ap.password)
            port = ap.api_port or (443 if vendor == "ubiquiti" else 8729)
            ap_monitor_interval = ap.monitor_interval or 2

            # Prepare credentials for scheduler
            creds = {"username": username, "password": password, "vendor": vendor, "port": port}

        # 2. Subscribe to scheduler (starts shared polling if first subscriber)
        await ap_monitor_scheduler.subscribe(host, creds, interval=ap_monitor_interval)
        print(f"✅ WS AP: Subscribed to scheduler for {host}")

        # 3. Loop reading from cache
        stats_cache = cache_manager.get_store("ap_stats")

        while True:
            # Determine interval
            if ap_monitor_interval and ap_monitor_interval >= 1:
                interval = ap_monitor_interval
            else:
                interval_setting = settings_db.get_setting("dashboard_refresh_interval")
                try:
                    interval = int(interval_setting) if interval_setting else 2
                    if interval < 1:
                        interval = 1
                except ValueError:
                    interval = 2

            # Read from cache
            data = stats_cache.get(host)

            if data:
                if "error" in data:
                    # Error in polling - notify but don't close
                    await websocket.send_json({"type": "error", "data": {"message": data["error"]}})
                else:
                    # Transform data for frontend compatibility
                    clients_list = []
                    for client in data.get("clients", []):
                        clients_list.append(
                            {
                                "cpe_mac": client.get("mac"),
                                "cpe_hostname": client.get("hostname"),
                                "ip_address": client.get("ip_address"),
                                "signal": client.get("signal"),
                                "signal_chain0": client.get("signal_chain0"),
                                "signal_chain1": client.get("signal_chain1"),
                                "noisefloor": client.get("noisefloor"),
                                "dl_capacity": client.get("extra", {}).get("dl_capacity")
                                if client.get("extra")
                                else None,
                                "ul_capacity": client.get("extra", {}).get("ul_capacity")
                                if client.get("extra")
                                else None,
                                "throughput_rx_kbps": client.get("rx_throughput_kbps"),
                                "throughput_tx_kbps": client.get("tx_throughput_kbps"),
                                "total_rx_bytes": client.get("rx_bytes"),
                                "total_tx_bytes": client.get("tx_bytes"),
                                "ccq": client.get("ccq"),
                                "tx_rate": client.get("tx_rate"),
                                "rx_rate": client.get("rx_rate"),
                            }
                        )

                    # Calculate memory usage
                    memory_usage = 0
                    extra = data.get("extra", {})
                    free_mem = extra.get("free_memory")
                    total_mem = extra.get("total_memory")

                    if free_mem and total_mem:
                        try:
                            free = int(free_mem)
                            total = int(total_mem)
                            if total > 0:
                                used = total - free
                                memory_usage = int(round((used / total) * 100, 1))
                        except (ValueError, TypeError):
                            pass

                    payload = {
                        "type": "resources",
                        "data": {
                            "host": host,
                            "hostname": data.get("hostname"),
                            "model": data.get("model"),
                            "mac": data.get("mac"),
                            "firmware": data.get("firmware"),
                            "vendor": data.get("vendor", vendor),
                            "client_count": data.get("client_count", 0),
                            "noise_floor": data.get("noise_floor"),
                            "chanbw": data.get("chanbw"),
                            "frequency": data.get("frequency"),
                            "essid": data.get("essid"),
                            "total_tx_bytes": data.get("total_tx_bytes"),
                            "total_rx_bytes": data.get("total_rx_bytes"),
                            "total_throughput_tx": data.get("total_throughput_tx"),
                            "total_throughput_rx": data.get("total_throughput_rx"),
                            "airtime_total_usage": data.get("airtime_total_usage"),
                            "airtime_tx_usage": data.get("airtime_tx_usage"),
                            "airtime_rx_usage": data.get("airtime_rx_usage"),
                            "clients": clients_list,
                            "extra": {
                                "cpu_load": extra.get("cpu_load", 0),
                                "free_memory": free_mem,
                                "total_memory": total_mem,
                                "memory_usage": memory_usage,
                                "uptime": extra.get("uptime", "--"),
                                "platform": extra.get("platform"),
                                "wireless_type": extra.get("wireless_type"),
                            },
                        },
                    }
                    await websocket.send_json(payload)
            else:
                # Data not yet available (loading...)
                await websocket.send_json({"type": "loading", "data": {}})

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        print(f"✅ WS AP: Cliente desconectado del stream {host}")
    except Exception as e:
        import traceback

        print(f"❌ WS AP Error crítico en {host}: {e}")
        traceback.print_exc()
    finally:
        # 4. Unsubscribe (important - cleanup when last user disconnects)
        await ap_monitor_scheduler.unsubscribe(host)
        try:
            await websocket.close()
        except:
            pass


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
    from ...core.audit import log_action

    try:
        await service.delete_ap(host)
        log_action("DELETE", "ap", host, user=current_user, request=request)
        return
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
    from ...db.engine import async_session_maker
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


# --- Provisioning Endpoints (MikroTik APs Only) ---


@router.post("/aps/{host}/provision")
async def provision_ap(
    host: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),  # Admin only
):
    """
    Provisions a MikroTik AP with secure API-SSL access.

    Creates a dedicated API user and installs SSL certificates.
    Only works for MikroTik APs (vendor='mikrotik').
    """
    import logging

    from ...core.audit import log_action
    from ...models.ap import AP as APModel
    from ...services.provisioning import MikrotikProvisioningService
    from ...services.provisioning.models import ProvisionRequest, ProvisionResponse
    from ...utils.security import decrypt_data, encrypt_data

    logger = logging.getLogger(__name__)

    # Parse request body
    try:
        body = await request.json()
        data = ProvisionRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    # 1. Get AP from database
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")

    # 2. Validate vendor
    if ap.vendor != "mikrotik":
        raise HTTPException(
            status_code=400,
            detail=f"Provisioning only available for MikroTik devices. This AP is: {ap.vendor}",
        )

    # 3. Check if already provisioned
    if ap.is_provisioned:
        raise HTTPException(
            status_code=400,
            detail="AP is already provisioned. Contact administrator to re-provision.",
        )

    # 4. Decrypt current password
    current_password = decrypt_data(ap.password)
    ssl_port = ap.api_ssl_port or 8729

    # 5. Record provisioning attempt
    ap.last_provision_attempt = datetime.now()
    ap.last_provision_error = None
    await session.commit()

    try:
        # 6. Run provisioning
        result = await MikrotikProvisioningService.provision_device(
            host=host,
            current_username=ap.username,
            current_password=current_password,
            new_user=data.new_api_user,
            new_password=data.new_api_password,
            ssl_port=ssl_port,
            method=data.method,
            device_type="ap",
        )

        if result["status"] == "error":
            # Update error tracking
            ap.last_provision_error = result["message"]
            await session.commit()
            raise HTTPException(status_code=500, detail=result["message"])

        # 7. Update AP in database
        ap.username = data.new_api_user
        ap.password = encrypt_data(data.new_api_password)
        ap.api_port = ssl_port  # Now use SSL port for connections
        ap.is_provisioned = True
        await session.commit()

        # 8. Audit log
        log_action("PROVISION", "ap", host, user=current_user, request=request)

        # 9. Reconnect to monitor scheduler with new credentials
        from ...services.ap_monitor_scheduler import ap_monitor_scheduler

        try:
            await asyncio.sleep(2)  # Wait for API-SSL restart on device
            new_creds = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "vendor": "mikrotik",
                "port": ssl_port,
            }
            await ap_monitor_scheduler.subscribe(host, new_creds)
        except Exception as e:
            logger.warning(f"Could not reconnect to scheduler after provisioning {host}: {e}")
            # Don't fail - scheduler will pick it up on next poll

        return ProvisionResponse(
            status="success",
            message="AP provisioned successfully with API-SSL",
            method_used=data.method,
        )

    except HTTPException:
        raise
    except Exception as e:
        ap.last_provision_error = str(e)
        await session.commit()
        logger.error(f"Provisioning failed for AP {host}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aps/{host}/provision-status")
async def get_provision_status(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Check the provisioning status of an AP.
    Returns whether provisioning is available and current status.
    """
    from ...models.ap import AP as APModel
    from ...services.provisioning.models import ProvisionStatus

    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")

    return ProvisionStatus(
        host=host,
        is_provisioned=ap.is_provisioned,
        vendor=ap.vendor or "unknown",
        api_port=ap.api_port or 443,
        api_ssl_port=ap.api_ssl_port or 8729,
        can_provision=(ap.vendor == "mikrotik" and not ap.is_provisioned),
        last_provision_attempt=ap.last_provision_attempt,
        last_provision_error=ap.last_provision_error,
    )


# --- Repair/Recovery Endpoint for APs ---
@router.post("/aps/{host}/repair", status_code=status.HTTP_200_OK)
async def repair_ap_connection(
    host: str,
    reset_provision: bool = False,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Repara/recupera un AP MikroTik que está en estado de error.

    Acciones que realiza:
    1. Limpia el estado de backoff (errores consecutivos)
    2. Limpia la caché de conexiones
    3. Si reset_provision=True, marca is_provisioned=False para permitir re-aprovisionar

    Args:
        host: IP del AP
        reset_provision: Si es True, permite volver a ejecutar el aprovisionamiento SSL

    Returns:
        Estado de la operación y siguientes pasos recomendados
    """
    from ...core.audit import log_action
    from ...models.ap import AP as APModel
    from ...services.ap_monitor_scheduler import ap_monitor_scheduler

    # 1. Verificar que el AP existe
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP no encontrado")

    # 2. Solo para MikroTik APs
    if ap.vendor != "mikrotik":
        raise HTTPException(
            status_code=400,
            detail=f"La reparación de aprovisionamiento solo aplica para MikroTik. Este AP es: {ap.vendor}",
        )

    # 3. Reset connection state in scheduler (if available)
    reset_result = {"message": "Estado de conexión limpiado."}
    try:
        if hasattr(ap_monitor_scheduler, "reset_connection"):
            reset_result = ap_monitor_scheduler.reset_connection(host)
    except Exception as e:
        reset_result = {"message": f"Advertencia al limpiar caché: {e}"}

    # 4. Opcionalmente marcar como no aprovisionado para re-aprovisionar
    if reset_provision:
        ap.is_provisioned = False
        ap.last_provision_error = None
        await session.commit()
        reset_result["provision_reset"] = "true"
        reset_result["message"] = (
            "Estado de aprovisionamiento reseteado. Listo para re-aprovisionar SSL."
        )

    # 5. Audit log
    log_action(
        "REPAIR", "ap", host, user=current_user, details={"reset_provision": reset_provision}
    )

    return {
        "status": "success",
        "message": reset_result.get("message", "Operación completada"),
        "provision_reset": reset_provision,
        "next_steps": [
            "Intente conectar nuevamente desde el Dashboard",
            "Si persisten errores SSL, use reset_provision=true para re-aprovisionar",
            "Verifique que el AP esté encendido y accesible en la red",
        ]
        if not reset_provision
        else [
            "El AP ahora muestra el botón 'Provision' en la lista",
            "Haga clic en 'Provision' para re-configurar SSL",
            "Use las credenciales admin del AP",
        ],
    }
