# app/api/routers/main.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from typing import List
import ssl
from routeros_api import RouterOsApiPool
import asyncio
import logging

from ...core.users import require_admin, require_technician
from ...models.user import User
from ...db import settings_db
from ...db.engine import get_session
from ...services.monitor_service import MonitorService
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

# --- CAMBIO PRINCIPAL: Importación actualizada a la nueva estructura modular ---
# Antes: from ...utils.device_clients.mikrotik_client import provision_router_api_ssl
from ...utils.device_clients.mikrotik.system import provision_router_api_ssl

from .models import (
    RouterResponse,
    RouterCreate,
    RouterUpdate,
    ProvisionRequest,
    ProvisionResponse,
)
from . import config, pppoe, system, interfaces

router = APIRouter()


@router.websocket("/routers/{host}/ws/resources")
async def router_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del router (CPU, RAM, etc).
    Lee el intervalo de refresco dinámicamente desde la configuración.
    """
    await websocket.accept()
    service = None

    try:
        # 1. Get router from DB using async session
        from ...db.engine import async_session_maker
        from ...services.router_service import get_router_by_host
        from ...utils.security import decrypt_data
        
        async with async_session_maker() as session:
            router = await get_router_by_host(session, host)
            if not router:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Router {host} no encontrado"}
                })
                await websocket.close()
                return
        
        # 2. Decrypt password and create service (OUTSIDE async with)
        password = decrypt_data(router.password)
        service = RouterService(host, router, decrypted_password=password)
        print(f"✅ WS: RouterService creado para {host}")

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
            data = await asyncio.to_thread(service.get_system_resources)

            # --- C. Preparar Payload ---
            payload = {
                "type": "resources",
                "data": {
                    "cpu_load": data.get("cpu-load", 0),
                    "free_memory": data.get("free-memory", 0),
                    "total_memory": data.get("total-memory", 0),
                    "uptime": data.get("uptime", "--"),
                    "total_disk": data.get("total-disk", 0),
                    "free_disk": data.get("free-disk", 0),
                    "voltage": data.get("voltage"),
                    "temperature": data.get("temperature"),
                    "cpu_temperature": data.get("cpu-temperature"),
                },
            }

            # --- D. Enviar al Cliente ---
            await websocket.send_json(payload)

            # --- E. Dormir ---
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        print(f"✅ WS: Cliente desconectado del stream {host}")
    except Exception as e:
        import traceback
        print(f"❌ WS Error crítico en {host}: {e}")
        traceback.print_exc()
    finally:
        if service:
            service.disconnect()
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
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    success = await delete_router_service(session, host)
    if not success:
        raise HTTPException(status_code=404, detail="Router not found to delete.")
    return


@router.post("/routers/{host}/provision", response_model=ProvisionResponse)
async def provision_router_endpoint(
    host: str,
    data: ProvisionRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    creds = await get_router_by_host_service(session, host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    # Decrypt password for connection
    from ...utils.security import decrypt_data
    password = decrypt_data(creds.password)

    admin_pool: RouterOsApiPool = None
    try:
        # Conexión inicial insegura (sin SSL) para configurar el SSL
        # Run blocking connection in thread
        def connect_and_provision():
            admin_pool = RouterOsApiPool(
                creds.host,
                username=creds.username,
                password=password,
                port=creds.api_port,
                use_ssl=False,
                plaintext_login=True,
            )
            api = admin_pool.get_api()

            # Llamada a la función modularizada
            result = provision_router_api_ssl(
                api, host, data.new_api_user, data.new_api_password
            )
            admin_pool.disconnect()
            return result

        result = await asyncio.to_thread(connect_and_provision)

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        # Actualizar DB con el nuevo usuario y puerto seguro
        update_data = {
            "username": data.new_api_user,
            "password": data.new_api_password,
            "api_port": creds.api_ssl_port,
        }
        await update_router_service(session, host, update_data)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if admin_pool:
            admin_pool.disconnect()


# --- Inclusión de los otros módulos de la API de routers ---
router.include_router(config.router, prefix="/routers/{host}")
router.include_router(pppoe.router, prefix="/routers/{host}")
router.include_router(system.router, prefix="/routers/{host}")
router.include_router(interfaces.router, prefix="/routers/{host}")


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
        # Esto conecta, descarga info (CPU, Ver, etc) y actualiza la DB a 'online'
        # MonitorService still uses router_db, so we pass the dict representation if needed
        # Or update MonitorService. For now, MonitorService expects dict-like or we need to check.
        # MonitorService.check_router calls router_db.update_router_status.
        # We should convert creds (Router model) to dict if MonitorService expects dict.
        # Let's assume MonitorService needs refactoring or we pass dict.
        creds_dict = creds.model_dump()
        # Add password decrypted? MonitorService decrypts it? 
        # MonitorService calls RouterService(host) which loads from DB.
        # Wait, MonitorService.check_router(creds) -> RouterService(host).
        # RouterService now requires 'creds' in __init__.
        # MonitorService needs to be updated to pass creds to RouterService!
        
        # Since we haven't refactored MonitorService yet, this call might fail if MonitorService instantiates RouterService(host).
        # We MUST refactor MonitorService or at least check_router method.
        
        # Temporary fix: We will run check_router in thread, but check_router needs to be compatible with new RouterService.
        # I will update MonitorService in next step.
        
        await asyncio.to_thread(monitor.check_router, creds_dict)
        return {
            "status": "success",
            "message": "Conexión verificada y datos actualizados.",
        }
    except Exception as e:
        # Logueamos el error pero no rompemos la API si el router no responde
        raise HTTPException(status_code=500, detail=f"Fallo al conectar: {str(e)}")
