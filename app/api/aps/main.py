# app/api/aps/main.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.engine import get_session, async_session_maker
from ...db import settings_db

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


# --- WebSocket Stream para Datos en Vivo (Mismo patrón que Routers) ---
@router.websocket("/ws/aps/{host}/resources")
async def ap_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del AP (CPU, RAM, etc).
    Usa el mismo mecanismo que Routers: UNA conexión durante toda la sesión.
    """
    from ...utils.device_clients.adapter_factory import get_device_adapter
    from ...utils.security import decrypt_data
    from ...models.ap import AP as APModel
    from ...utils.device_clients.mikrotik import system as mikrotik_system
    
    await websocket.accept()
    adapter = None

    try:
        # 1. Get AP from DB
        async with async_session_maker() as session:
            ap = await session.get(APModel, host)
            if not ap:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"AP {host} no encontrado"}
                })
                await websocket.close()
                return
            
            # Copy needed data before session closes
            vendor = ap.vendor or "mikrotik"
            username = ap.username
            password = decrypt_data(ap.password)
            port = ap.api_port or (443 if vendor == "ubiquiti" else 8729)
        
        # 2. Create adapter (OUTSIDE async with) - ONE connection for whole stream
        adapter = get_device_adapter(
            host=host,
            username=username,
            password=password,
            vendor=vendor,
            port=port,
        )
        print(f"✅ WS AP: Adapter creado para {host}")

        while True:
            # --- A. Leer Configuración Dinámica ---
            interval_setting = settings_db.get_setting("dashboard_refresh_interval")

            try:
                interval = int(interval_setting) if interval_setting else 2
                if interval < 1:
                    interval = 1
            except ValueError:
                interval = 2

            # --- B. Obtener Datos (Non-blocking) ---
            status = await asyncio.to_thread(adapter.get_status)

            # --- C. Preparar Payload (same format as HTTP /live endpoint) ---
            if status and status.is_online:
                # Convert clients to serializable format
                clients_list = []
                for client in status.clients:
                    clients_list.append({
                        "cpe_mac": client.mac,
                        "cpe_hostname": client.hostname,
                        "ip_address": client.ip_address,
                        "signal": client.signal,
                        "signal_chain0": client.signal_chain0,
                        "signal_chain1": client.signal_chain1,
                        "noisefloor": client.noisefloor,
                        "dl_capacity": client.extra.get("dl_capacity") if client.extra else None,
                        "ul_capacity": client.extra.get("ul_capacity") if client.extra else None,
                        "throughput_rx_kbps": client.rx_throughput_kbps,
                        "throughput_tx_kbps": client.tx_throughput_kbps,
                        "total_rx_bytes": client.rx_bytes,
                        "total_tx_bytes": client.tx_bytes,
                        "ccq": client.ccq,
                        "tx_rate": client.tx_rate,
                        "rx_rate": client.rx_rate,
                    })
                
                # Format uptime
                uptime_str = "--"
                if status.uptime:
                    days = status.uptime // 86400
                    hours = (status.uptime % 86400) // 3600
                    minutes = (status.uptime % 3600) // 60
                    if days > 0:
                        uptime_str = f"{days}d {hours}h {minutes}m"
                    elif hours > 0:
                        uptime_str = f"{hours}h {minutes}m"
                    else:
                        uptime_str = f"{minutes}m"
                
                # Calculate memory usage
                memory_usage = 0
                free_mem = status.extra.get("free_memory") if status.extra else None
                total_mem = status.extra.get("total_memory") if status.extra else None
                
                if free_mem and total_mem:
                    try:
                        free = int(free_mem)
                        total = int(total_mem)
                        if total > 0:
                            used = total - free
                            memory_usage = round((used / total) * 100, 1)
                    except (ValueError, TypeError):
                        pass

                payload = {
                    "type": "resources",
                    "data": {
                        "host": host,
                        "hostname": status.hostname,
                        "model": status.model,
                        "mac": status.mac,
                        "firmware": status.firmware,
                        "vendor": vendor,
                        "client_count": status.client_count or 0,
                        "noise_floor": status.noise_floor,
                        "chanbw": status.channel_width,
                        "frequency": status.frequency,
                        "essid": status.essid,
                        "total_tx_bytes": status.tx_bytes,
                        "total_rx_bytes": status.rx_bytes,
                        "total_throughput_tx": status.tx_throughput,
                        "total_throughput_rx": status.rx_throughput,
                        "airtime_total_usage": status.airtime_usage,
                        "airtime_tx_usage": status.extra.get("airtime_tx") if status.extra else None,
                        "airtime_rx_usage": status.extra.get("airtime_rx") if status.extra else None,
                        "clients": clients_list,
                        # Structure specific to ap_details_mikrotik.js compatibility
                        "extra": {
                            "cpu_load": status.extra.get("cpu_load", 0) if status.extra else 0,
                            "free_memory": free_mem,
                            "total_memory": total_mem,
                            "memory_usage": memory_usage,
                            "uptime": uptime_str,
                            "platform": status.extra.get("platform") if status.extra else None,
                            "wireless_type": status.extra.get("wireless_type") if status.extra else None,
                        }
                    },
                }
            else:
                payload = {
                    "type": "error",
                    "data": {"message": status.last_error or "AP no responde"}
                }

            # --- D. Enviar al Cliente ---
            await websocket.send_json(payload)

            # --- E. Dormir ---
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        print(f"✅ WS AP: Cliente desconectado del stream {host}")
    except Exception as e:
        import traceback
        print(f"❌ WS AP Error crítico en {host}: {e}")
        traceback.print_exc()
    finally:
        # Solo cerrar cuando el WebSocket se cierra
        if adapter:
            adapter.disconnect()
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
