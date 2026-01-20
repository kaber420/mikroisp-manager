# app/api/routers/main.py
import asyncio
import logging

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

from ...core.users import require_admin, require_technician
from ...db import settings_db
from ...db.engine import get_session
from ...models.user import User
from ...services.monitor_scheduler import monitor_scheduler
from ...services.provisioning import MikrotikProvisioningService
from ...services.router_service import RouterService
from ...services.router_service import create_router as create_router_service
from ...services.router_service import delete_router as delete_router_service
from ...services.router_service import get_all_routers as get_all_routers_service
from ...services.router_service import get_router_by_host as get_router_by_host_service
from ...services.router_service import update_router as update_router_service
from ...utils.cache import cache_manager
from . import config, interfaces, pppoe, system
from . import ssl as ssl_router
from .models import (
    ProvisionRequest,
    ProvisionResponse,
    RouterCreate,
    RouterResponse,
    RouterUpdate,
)

router = APIRouter()


@router.websocket("/routers/{host}/ws/resources")
async def router_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del router (CPU, RAM, etc).

    IMPLEMENTACIÓN V2 (Cache In-Memory + Scheduler):
    - NO conecta al router directamente.
    - Se suscribe al MonitorScheduler.
    - Lee del CacheManager local.
    """
    await websocket.accept()

    # 1. Obtener credenciales (BD)
    from ...db.engine import async_session_maker
    from ...services.router_service import get_router_by_host
    from ...utils.security import decrypt_data

    async with async_session_maker() as session:
        router = await get_router_by_host(session, host)
        if not router:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Preparar credenciales para el scheduler
        creds = {
            "username": router.username,
            "password": decrypt_data(router.password),
            "port": router.api_ssl_port,
        }

    # 2. Suscribir al Scheduler (esto inicia la conexión background si es necesario)
    await monitor_scheduler.subscribe(host, creds)

    try:
        # 3. Loop de lectura del Cache
        stats_cache = cache_manager.get_store("router_stats")

        while True:
            # Leer intervalo dinámico
            interval_setting = settings_db.get_setting("dashboard_refresh_interval")
            try:
                interval = max(1, int(interval_setting or 2))
            except:
                interval = 2

            # Leer del Cache
            data = stats_cache.get(host)

            if data:
                if "error" in data:
                    # Si hay error en el polling, notificar pero no cerrar
                    await websocket.send_json({"type": "error", "data": {"message": data["error"]}})
                else:
                    # Mapeo de datos para frontend (compatible con V1)
                    payload = {
                        "type": "resources",
                        "data": {
                            "cpu_load": data.get("cpu_load", 0),
                            "free_memory": data.get("free_memory", 0),
                            "total_memory": data.get("total_memory", 0),
                            "uptime": data.get("uptime", "--"),
                            "total_disk": data.get("total_disk", 0),
                            "free_disk": data.get("free_disk", 0),
                            "voltage": data.get("voltage"),
                            "temperature": data.get("temperature"),
                            "cpu_temperature": data.get("cpu_temperature"),
                        },
                    }
                    await websocket.send_json(payload)
            else:
                # Datos aun no disponibles (cargando...)
                await websocket.send_json({"type": "loading", "data": {}})

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"❌ WS Error en {host}: {e}")
    finally:
        # 4. Desuscribir (importante para cerrar conexión si es el último)
        await monitor_scheduler.unsubscribe(host)
        try:
            await websocket.close()
        except:
            pass


# --- Endpoints CRUD (Gestión de Routers en BD) ---
@router.get("/routers", response_model=list[RouterResponse])
async def get_all_routers(
    current_user: User = Depends(require_technician), session: AsyncSession = Depends(get_session)
):
    return await get_all_routers_service(session)


@router.get("/routers/{host}", response_model=RouterResponse)
async def get_router(
    host: str,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session),
):
    router_data = await get_router_by_host_service(session, host)
    if not router_data:
        raise HTTPException(status_code=404, detail="Router not found")
    return router_data


@router.post("/routers", response_model=RouterResponse, status_code=status.HTTP_201_CREATED)
async def create_router(
    router_data: RouterCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        new_router = await create_router_service(session, router_data.model_dump())

        # --- AUTO-PROVISION SSL (Zero Trust) ---
        # DISABLE AUTO-PROVISION per user request (point of failure)
        # await ProvisioningService.auto_provision_ssl(session, new_router)

        return new_router
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/routers/{host}", response_model=RouterResponse)
async def update_router(
    host: str,
    router_data: RouterUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    update_fields = router_data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update provided.")

    if "password" in update_fields and not update_fields["password"]:
        del update_fields["password"]

    updated_router = await update_router_service(session, host, update_fields)
    if not updated_router:
        raise HTTPException(status_code=404, detail="Router not found.")

    return updated_router


@router.delete("/routers/{host}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_router(
    host: str,
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    from ...core.audit import log_action

    success = await delete_router_service(session, host)
    if not success:
        raise HTTPException(status_code=404, detail="Router not found to delete.")
    log_action("DELETE", "router", host, user=current_user, request=request)
    return


@router.post("/routers/{host}/provision", response_model=ProvisionResponse)
async def provision_router_endpoint(
    host: str,
    data: ProvisionRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Unified Provisioning Endpoint.
    Creates a dedicated API user and installs a trusted SSL certificate via SSH.
    Uses the shared MikrotikProvisioningService for all MikroTik devices.
    """
    from ...core.audit import log_action
    from ...utils.security import decrypt_data

    # 1. Get router from database
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    # 2. Decrypt current password
    current_password = decrypt_data(creds.password)
    ssl_port = creds.api_ssl_port or 8729

    try:
        # 3. Run provisioning via shared service
        result = await MikrotikProvisioningService.provision_device(
            host=host,
            current_username=creds.username,
            current_password=current_password,
            new_user=data.new_api_user,
            new_password=data.new_api_password,
            ssl_port=ssl_port,
            method=data.method,
            device_type="router",
            current_api_port=creds.api_port or 8728,
        )

        if result.get("status") == "error":
            raise HTTPException(
                status_code=500, detail=result.get("message", "Provisioning failed")
            )

        # 4. Update router in database with new credentials
        update_data = {
            "username": data.new_api_user,
            "password": data.new_api_password,
            "api_port": ssl_port,  # Now use SSL port for connections
            "is_provisioned": True,
        }
        await update_router_service(session, host, update_data)

        # 5. Audit log
        log_action("PROVISION", "router", host, user=current_user, request=request)

        # 6. Return successful response
        return ProvisionResponse(
            status="success",
            message=result.get("message", "Router provisioned successfully with API-SSL"),
            method_used=result.get("method_used", data.method),
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Provisioning failed for {host}: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- Simple Queue Stats Endpoint ---
@router.get("/routers/{host}/queue/stats")
async def get_queue_stats(
    host: str,
    target: str,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session),
):
    """
    Get live stats for a Simple Queue by target IP.
    Returns bytes-in, bytes-out, max-limit, etc.
    """
    from ...utils.security import decrypt_data

    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router not found")

    try:
        password = decrypt_data(creds.password)
        with RouterService(host, creds, decrypted_password=password) as rs:
            stats = rs.get_simple_queue_stats(target)
            if not stats:
                return {"status": "not_found", "message": f"No queue found for target {target}"}
            return {
                "status": "success",
                "name": stats.get("name"),
                "target": stats.get("target"),
                "max-limit": stats.get("max-limit"),
                "bytes": stats.get("bytes"),  # "upload/download" format
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching queue stats: {e}")


# --- Router Historical Stats Endpoint ---
@router.get("/routers/{host}/history")
async def get_router_history(
    host: str,
    range_hours: int = 24,
    current_user: User = Depends(require_technician),
):
    """
    Get historical stats for a router (CPU, Memory, etc.) over time.
    Default range is last 24 hours.
    """
    from ...db.stats_db import get_router_monitor_stats_history

    data = get_router_monitor_stats_history(host, range_hours)
    return {"status": "success", "data": data}


# --- Inclusión de los otros módulos de la API de routers ---
router.include_router(config.router, prefix="/routers/{host}")
router.include_router(pppoe.router, prefix="/routers/{host}")
router.include_router(system.router, prefix="/routers/{host}")
router.include_router(interfaces.router, prefix="/routers/{host}")
router.include_router(ssl_router.router, prefix="/routers/{host}")


# --- NUEVO ENDPOINT PARA CONEXIÓN AUTOMÁTICA ---
@router.post("/routers/{host}/check", status_code=status.HTTP_200_OK)
async def check_router_status_manual(
    host: str,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session),
):
    """
    Fuerza al monitor a leer los datos del router INMEDIATAMENTE.
    Actualiza tanto el cache (para gráficas) como la DB (para la lista).
    """
    from ...utils.security import decrypt_data

    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    if not creds.is_enabled:
        raise HTTPException(status_code=400, detail="El router está deshabilitado.")

    if creds.api_port != creds.api_ssl_port:
        raise HTTPException(status_code=400, detail="El router no está aprovisionado (SSL).")

    try:
        # Prepare credentials
        router_creds = {
            "username": creds.username,
            "password": decrypt_data(creds.password),
            "port": creds.api_ssl_port,
        }

        # Subscribe and refresh immediately (updates cache + DB)
        await monitor_scheduler.subscribe(host, router_creds)
        result = await monitor_scheduler.refresh_host(host)

        if "error" in result:
            return {
                "status": "error",
                "message": f"No se pudo conectar: {result['error']}",
            }

        return {
            "status": "success",
            "message": "Estado actualizado correctamente.",
            "data": {
                "uptime": result.get("uptime"),
                "version": result.get("version"),
            },
        }
    except Exception as e:
        logging.error(f"check_router_status_manual failed for {host}: {e}")
        raise HTTPException(status_code=500, detail=f"Fallo al conectar: {str(e)}")


# --- ENDPOINT DE REPARACIÓN/RECUPERACIÓN ---
@router.post("/routers/{host}/repair", status_code=status.HTTP_200_OK)
async def repair_router_connection(
    host: str,
    reset_provision: bool = False,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Repara/recupera un router que está en estado de error.

    Acciones que realiza:
    1. Limpia el estado de backoff (errores consecutivos)
    2. Limpia la caché de conexiones
    3. Limpia el pool de conexiones SSL
    4. Si reset_provision=True, marca is_provisioned=False para permitir re-aprovisionar

    Args:
        host: IP del router
        reset_provision: Si es True, permite volver a ejecutar el aprovisionamiento SSL

    Returns:
        Estado de la operación y siguientes pasos recomendados
    """
    from ...core.audit import log_action

    # 1. Verificar que el router existe
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    # 2. Resetear estado de conexión en el scheduler
    reset_result = monitor_scheduler.reset_connection(host)

    # 3. Opcionalmente marcar como no aprovisionado para re-aprovisionar
    if reset_provision:
        update_data = {
            "is_provisioned": False  # Solo esto - NO cambiar puertos
        }
        await update_router_service(session, host, update_data)
        reset_result["provision_reset"] = True
        reset_result["message"] += " Listo para re-aprovisionar SSL."

    # 4. Audit log
    log_action(
        "REPAIR", "router", host, user=current_user, details={"reset_provision": reset_provision}
    )

    return {
        "status": "success",
        "message": reset_result["message"],
        "provision_reset": reset_provision,
        "next_steps": [
            "Intente conectar nuevamente desde el Dashboard",
            "Si persisten errores SSL, use reset_provision=true para re-aprovisionar",
            "Verifique que el router esté encendido y accesible en la red",
        ]
        if not reset_provision
        else [
            "El router ahora muestra el botón 'Provision' en la lista",
            "Haga clic en 'Provision' para re-configurar SSL",
            "Use las credenciales admin del router",
        ],
    }
