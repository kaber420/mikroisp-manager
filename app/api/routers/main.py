# app/api/routers/main.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
import asyncio
import logging
from typing import List, Optional
import ssl

from routeros_api import RouterOsApiPool

from ...core.users import require_admin, require_technician
from ...models.user import User
from ...db import settings_db
from ...db.engine import get_session
from ...services.monitor_service import MonitorService
from ...services.monitor_scheduler import monitor_scheduler
from ...utils.cache import cache_manager
from ...services.router_service import (
    RouterService, 
    get_all_routers as get_all_routers_service,
    get_router_by_host as get_router_by_host_service,
    create_router as create_router_service,
    update_router as update_router_service,
    delete_router as delete_router_service,
    get_router_service
)
from sqlalchemy.ext.asyncio import AsyncSession

# Note: provision_router_api_ssl is now deprecated and its logic is inline in the endpoint

from .models import (
    RouterResponse,
    RouterCreate,
    RouterUpdate,
    ProvisionRequest,
    ProvisionResponse,
)
from . import config, pppoe, system, interfaces, ssl as ssl_router

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
            "port": router.api_ssl_port
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
@router.get("/routers", response_model=List[RouterResponse])
async def get_all_routers(
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    return await get_all_routers_service(session)


@router.get("/routers/{host}", response_model=RouterResponse)
async def get_router(
    host: str, 
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    router_data = await get_router_by_host_service(session, host)
    if not router_data:
        raise HTTPException(status_code=404, detail="Router not found")
    return router_data


@router.post(
    "/routers", response_model=RouterResponse, status_code=status.HTTP_201_CREATED
)
async def create_router(
    router_data: RouterCreate, 
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    try:
        new_router = await create_router_service(session, router_data.model_dump())
        
        # --- AUTO-PROVISION SSL (Zero Trust) ---
        try:
             # Decrypt password for connection
            from ...utils.security import decrypt_data
            password = decrypt_data(new_router.password)
            
            # Init service (connects automatically)
            service = RouterService(new_router.host, new_router, decrypted_password=password)
            try:
                # Trigger auto-provisioning
                is_secure = service.ensure_ssl_provisioned()
                if is_secure:
                    # Update DB to reflect SSL port if it was different
                    if new_router.api_port != new_router.api_ssl_port:
                        await update_router_service(session, new_router.host, {"api_port": new_router.api_ssl_port})
                        # Refresh router object
                        new_router = await get_router_by_host_service(session, new_router.host)
            finally:
                service.disconnect()
        except Exception as e:
            # Log error but don't fail router creation
            logging.error(f"Failed to auto-provision SSL for {new_router.host}: {e}")

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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
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
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Unified Provisioning Endpoint.
    Creates a dedicated API user and installs a trusted SSL certificate via SSH.
    This is more secure than the legacy API-based provisioning.
    """
    from ...utils.security import decrypt_data, encrypt_data
    from ...services.pki_service import PKIService
    from ...utils.device_clients.adapters.mikrotik_router import MikrotikRouterAdapter
    
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    password = decrypt_data(creds.password)

    try:
        def run_provisioning():
            # 1. Connect to router (insecure API for initial setup)
            from routeros_api import RouterOsApiPool
            pool = RouterOsApiPool(
                creds.host,
                username=creds.username,
                password=password,
                port=creds.api_port,
                use_ssl=False,
                plaintext_login=True,
            )
            api = pool.get_api()
            
            try:
                # 2. Create dedicated API user with correct group
                user_group_name = "api_full_access"
                group_resource = api.get_resource("/user/group")
                group_list = group_resource.get(name=user_group_name)
                current_policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
                
                if not group_list:
                    group_resource.add(name=user_group_name, policy=current_policy)
                else:
                    from ...utils.device_clients.mikrotik.base import get_id
                    group_resource.set(id=get_id(group_list[0]), policy=current_policy)
                
                user_resource = api.get_resource("/user")
                existing_user = user_resource.get(name=data.new_api_user)
                if existing_user:
                    from ...utils.device_clients.mikrotik.base import get_id
                    user_resource.set(id=get_id(existing_user[0]), password=data.new_api_password, group=user_group_name)
                else:
                    user_resource.add(name=data.new_api_user, password=data.new_api_password, group=user_group_name)
                
                # 3. Setup SSL via PKI Service (secure SSH method)
                pki = PKIService()
                if not pki.verify_mkcert_available():
                    return {"status": "error", "message": "mkcert no está disponible. Instálalo para habilitar SSL."}
                
                # Install CA on router
                ca_pem = pki.get_ca_pem()
                if ca_pem:
                    # Create a temporary adapter for SSL operations (uses current creds)
                    temp_adapter = MikrotikRouterAdapter(host, creds.username, password, creds.api_port)
                    # We need to use API to install CA since SSH might not be ready
                    from ...utils.device_clients.mikrotik import ssl as ssl_module
                    ssl_module.install_ca_certificate(api, host, creds.username, password, ca_pem, "umanager_ca")
                    
                    # Generate and install router certificate
                    success, key_pem, cert_pem = pki.generate_full_cert_pair(host)
                    if success:
                        ssl_module.import_certificate(api, host, creds.api_ssl_port, data.new_api_user, data.new_api_password, cert_pem, key_pem, "umanager_ssl")
                    else:
                        return {"status": "error", "message": f"Error generando certificado: {cert_pem}"}
                
                return {"status": "success", "message": "Router aprovisionado con API-SSL seguro."}
            finally:
                pool.disconnect()
        
        result = await asyncio.to_thread(run_provisioning)

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        # Update DB: new user, password, SSL port, and mark as provisioned
        update_data = {
            "username": data.new_api_user,
            "password": data.new_api_password,
            "api_port": creds.api_ssl_port,
            "is_provisioned": True,
        }
        await update_router_service(session, host, update_data)
        return result

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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
):
    """
    Fuerza al monitor a leer los datos del router INMEDIATAMENTE.
    Se usa después de aprovisionar para poner el router 'Online' sin esperar 5 min.
    """
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    # Validaciones básicas antes de intentar conectar
    if not creds.is_enabled:
        raise HTTPException(status_code=400, detail="El router está deshabilitado.")

    if creds.api_port != creds.api_ssl_port:
        raise HTTPException(
            status_code=400, detail="El router no está aprovisionado (SSL)."
        )

    try:
        # Instanciamos el servicio y ejecutamos el chequeo síncrono
        monitor = MonitorService()
        
        # 1. Run Monitor Check (sync)
        await asyncio.to_thread(monitor.check_router, creds.model_dump())
        
        # 2. Run SSL Provisioning Check (sync logic wrapped in thread)
        def check_ssl_provisioning():
             from ...utils.security import decrypt_data
             password = decrypt_data(creds.password)
             with RouterService(host, creds, decrypted_password=password) as rs:
                 return rs.ensure_ssl_provisioned()

        is_secure = await asyncio.to_thread(check_ssl_provisioning)

        return {
            "status": "success",
            "message": "Conexión verificada y datos actualizados. SSL Secure: " + str(is_secure),
        }
    except Exception as e:
        # Logueamos el error pero no rompemos la API si el router no responde
        raise HTTPException(status_code=500, detail=f"Fallo al conectar: {str(e)}")
