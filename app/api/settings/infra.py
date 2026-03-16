from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Cookie
import asyncio
import secrets
from typing import Optional, Dict
from pydantic import BaseModel

from app.core.security import require_admin
from ...models.user import User
from ...services.core.infrastructure_service import InfrastructureService
from ...core.audit import log_action
from ...core.config import settings

router = APIRouter()


def get_infra_service():
    return InfrastructureService()


class AdvancedConfig(BaseModel):
    env: dict = {}
    network: str = "bridge"
    port: Optional[int] = None
    volumes: Optional[dict] = None

class ServiceAction(BaseModel):
    postgres: str = "skip"   # "create" | "reuse" | "skip" | "reset" | "delete" | "stop"
    redict: str = "skip"     # "create" | "reuse" | "skip" | "reset" | "delete" | "stop"


class DeployRequest(BaseModel):
    postgres_password: Optional[str] = None
    postgres_user: Optional[str] = "umanager"
    postgres_db: Optional[str] = "umanager_db"
    actions: ServiceAction = ServiceAction()
    advanced: Optional[Dict[str, AdvancedConfig]] = None


@router.get("/status", response_model=dict)
async def api_get_infra_status(
    service: InfrastructureService = Depends(get_infra_service),
    current_user: User = Depends(require_admin),
):
    """
    Lista el estado en vivo de los componentes Docker.
    Ahora detecta conflictos de puertos con otros contenedores del host.
    Requiere SuperAdmin.
    """
    return service.check_services_status()


@router.post("/deploy", status_code=status.HTTP_200_OK)
async def api_deploy_infrastructure(
    body: DeployRequest,
    service: InfrastructureService = Depends(get_infra_service),
    current_user: User = Depends(require_admin),
):
    """
    Despliega PostgreSQL y Redict respetando las acciones elegidas por el usuario.
    Permite configuración manual de credenciales antes del lanzamiento.
    actions.postgres / actions.redict: "create" | "reuse" | "skip" | "reset" | "delete" | "stop"
    """
    # Si el usuario no mandó password, solo generamos una si la acción es "create" pura 
    # y no tenemos una previa configurada.
    postgres_password = body.postgres_password
    
    if not postgres_password and body.actions.postgres in ["create", "reset"]:
        from app.utils.services_config import read_services_config
        srv = read_services_config()
        # Intentar reusar la existente si existe en config
        postgres_password = srv.get("db", {}).get("password")
        
        # Si sigue sin haber nada, solo entonces generamos (emergencia)
        if not postgres_password:
            postgres_password = secrets.token_urlsafe(20)

    # Extraer configs avanzadas si existen
    advanced_configs = {}
    if body.advanced:
        for k, v in body.advanced.items():
            advanced_configs[k] = v.model_dump()

    result = service.deploy_production_stack(
        postgres_password=postgres_password,
        postgres_user=body.postgres_user,
        postgres_db=body.postgres_db,
        actions=body.actions.model_dump(),
        advanced_configs=advanced_configs
    )

    if result.get("status") == "error":
        log_action(
            action="INFRA_DEPLOY",
            resource_type="system",
            resource_id="docker",
            user=current_user,
            status="failure",
            details={"error": result.get("message"), "actions": body.actions.model_dump()},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Error inesperado en Despliegue de Infra"),
        )

    log_action(
        action="INFRA_DEPLOY",
        resource_type="system",
        resource_id="docker",
        user=current_user,
        status="success",
        details={"actions": body.actions.model_dump()}
    )

    return {
        "message": "Operación de infraestructura completada.",
        "details": result.get("details"),
        "postgres_password": result.get("postgres_password")
    }


@router.websocket("/ws/logs/{container_name}")
async def websocket_logs(
    websocket: WebSocket,
    container_name: str,
    service: InfrastructureService = Depends(get_infra_service),
    umonitorpro_access_token_v2: Optional[str] = Cookie(None)
):
    """
    WebSocket para streaming de logs de contenedores en tiempo real.
    Utiliza el módulo centralizado de seguridad.
    """
    from ...core.security import verify_ws_origin_and_token
    import logging
    logger = logging.getLogger("app.websocket")

    if not await verify_ws_origin_and_token(
        websocket, 
        umonitorpro_access_token_v2, 
        allowed_roles=["admin"]
    ):
        return

    await websocket.accept()
    logger.info(f"🔌 WebSocket logs conectado para: {container_name}")
    
    try:
        # Logs en modo stream (generador síncrono del Docker SDK)
        log_generator = service.get_container_logs_stream(container_name)
        
        while True:
            try:
                # Ejecutar next() en un hilo para no bloquear el event loop
                line = await asyncio.to_thread(next, log_generator)
                if line:
                    await websocket.send_text(line)
            except StopIteration:
                break
            except Exception as e:
                logger.error(f"Error leyendo línea de log: {e}")
                break
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error en WebSocket logs para {container_name}: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
