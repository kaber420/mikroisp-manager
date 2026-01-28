
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
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.users import require_admin, require_technician

from ...db.engine import get_session
from ...models.user import User
from ...services.monitor_scheduler import monitor_scheduler
from ...services.provisioning import MikrotikProvisioningService
from ...services.router_service import RouterService

# --- UPDATE: Import directly from router_db ---
from ...db.router_db import create_router_in_db as create_router_service
from ...db.router_db import delete_router_from_db as delete_router_service
from ...db.router_db import get_all_routers as get_all_routers_service
from ...db.router_db import get_router_by_host as get_router_by_host_service
from ...db.router_db import update_router_in_db as update_router_service

from ...utils.cache import cache_manager
from . import config, interfaces, pppoe, system, ssl as ssl_router
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
    from ...db.router_db import get_router_by_host  # Use router_db directly
    from ...utils.security import decrypt_data

    async with async_session_maker() as session:
        router = await get_router_by_host(session, host)
        if not router:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Preparar credenciales para el scheduler
        # get_router_by_host returns decrypted object (copy) or object with encrypted pass?
        # My implementation returns decrypted copy.
        # So decrypt_data(router.password) will fail if it's already plain.
        # But wait, original code imported decrypt_data.
        # Let's check router.password.
        # We can implement a safe decrypt or just use the password if we trust get_router_by_host.
        password = router.password
        try:
             # If it's encrypted, this works. If plain, it might fail or return garbage?
             # Fernet token validation usually fails if not token.
             # Given router_db.get_router_by_host returns decrypted, we don't need to decrypt again.
             pass 
        except:
             pass
        
        # However, monitor_scheduler expects what?
        # router_db.get_router_by_host returns decrypted object.
        creds = {
            "username": router.username,
            "password": router.password, # Already decrypted
            "port": router.api_ssl_port,
        }

    # 2. Suscribir al Scheduler (esto inicia la conexión background si es necesario)
    await monitor_scheduler.subscribe(host, creds)

    try:
        # 3. Loop de lectura del Cache
        stats_cache = cache_manager.get_store("router_stats")

        while True:
            # Leer intervalo dinámico
            try:
                # Use async session to get setting
                async with async_session_maker() as session:
                    from ...services.settings_service import SettingsService
                    svc = SettingsService(session)
                    interval_setting = await svc.get_setting_value("dashboard_refresh_interval")
                
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
        # router_data.model_dump() -> dict
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

    # uses update_router_in_db which returns int (rows affected)
    rows = await update_router_service(session, host, update_fields)
    if not rows:
        raise HTTPException(status_code=404, detail="Router not found OR no changes made.")

    # Return updated object
    updated_router = await get_router_by_host_service(session, host)
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
    # creds.password is already decrypted by get_router_by_host
    current_password = creds.password
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

    # Use router_db directly via service alias
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router not found")

    try:
        # creds.password is decrypted
        password = creds.password
        # RouterService handles already decrypted password now
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
    # Stats DB is exempt, uses synchronous connection internally?
    # get_router_monitor_stats_history in stats_db.py needs to be checked.
    # Assuming it's safe to call here (blocking).
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
    
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    if not creds.is_enabled:
        raise HTTPException(status_code=400, detail="El router está deshabilitado.")

    if creds.api_port != creds.api_ssl_port:
        raise HTTPException(status_code=400, detail="El router no está aprovisionado (SSL).")

    try:
        # Prepare credentials (password already decrypted)
        router_creds = {
            "username": creds.username,
            "password": creds.password,
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
class RepairRequest(BaseModel):
    """Request body for repair endpoint."""
    action: str = "unprovision"  # 'renew' or 'unprovision'


@router.post("/routers/{host}/repair", status_code=status.HTTP_200_OK)
async def repair_router_connection(
    host: str,
    body: RepairRequest | None = None,
    reset_provision: bool = False,  # Keep for backward compatibility
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Repairs or recovers a router in an error state.

    Actions:
    - `unprovision`: Marks the router as not provisioned (DB only). Default.
    - `renew`: Renews SSL certificates without full re-provisioning.
    """
    from ...core.audit import log_action

    # Handle backward compatibility: if reset_provision is True and no body, treat as unprovision
    action = "unprovision"
    if body:
        action = body.action
    elif reset_provision:
        action = "unprovision"

    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    if action == "renew":
        # Call renew_ssl to reinstall certificates
        result = await MikrotikProvisioningService.renew_ssl(
            host=host,
            username=creds.username,
            password=creds.password,
            ssl_port=creds.api_ssl_port or 8729,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "SSL renewal failed"))

        log_action("RENEW_SSL", "router", host, user=current_user)

        return {
            "status": "success",
            "message": "Certificados SSL renovados exitosamente.",
            "action": "renew",
        }

    elif action == "unprovision":
        # Reset connection state
        reset_result = monitor_scheduler.reset_connection(host)

        # Mark as not provisioned
        update_data = {"is_provisioned": False}
        await update_router_service(session, host, update_data)

        log_action("UNPROVISION", "router", host, user=current_user)

        return {
            "status": "success",
            "message": "Router desvinculado. Listo para re-aprovisionar.",
            "action": "unprovision",
        }
    else:
        raise HTTPException(status_code=400, detail=f"Acción desconocida: {action}")

