# app/api/setup/infra.py
"""
Endpoints de infraestructura específicos para el Asistente de Instalación (Setup Wizard).
Permite configurar y desplegar Docker Postgres + Redict de manera pública
pero protegida mediante la guardia verify_system_not_setup.
"""

import asyncio
import logging
import secrets
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.engine import get_session
from app.models.user import User
from app.services.core.infrastructure_service import InfrastructureService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup - Infrastructure"])


def get_infra_service() -> InfrastructureService:
    return InfrastructureService()


async def verify_system_not_setup(session: AsyncSession = Depends(get_session)):
    """
    Guardia de seguridad absoluta:
    Si existe al menos un usuario en la base de datos, bloquea el endpoint con 403.
    """
    result = await session.execute(select(User).limit(1))
    if result.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El sistema ya ha sido configurado. Acceso denegado.",
        )


class SetupDeployRequest(BaseModel):
    postgres_password: Optional[str] = None
    postgres_user: Optional[str] = "umanager"
    postgres_db: Optional[str] = "umanager_db"
    actions: Dict[str, str] = {"postgres": "create", "redict": "create"}
    advanced: Optional[Dict[str, Any]] = None


class TestConnectionRequest(BaseModel):
    provider: str  # "postgres" | "sqlite" | "redict"
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None


@router.get("/status", response_model=dict)
async def get_setup_infra_status(
    service: InfrastructureService = Depends(get_infra_service),
    session: AsyncSession = Depends(get_session),
    _guard: None = Depends(verify_system_not_setup)
):
    """
    Retorna el estado de Docker y disponibilidad de puertos durante el setup.
    """
    try:
        status_info = service.check_services_status()
        return status_info
    except Exception as e:
        logger.error(f"Error checking infra status in setup: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/deploy-infra", response_model=dict)
async def deploy_setup_infra(
    body: SetupDeployRequest,
    service: InfrastructureService = Depends(get_infra_service),
    session: AsyncSession = Depends(get_session),
    _guard: None = Depends(verify_system_not_setup)
):
    """
    Despliega la pila de Docker PostgreSQL + Redict durante el setup.
    Genera credenciales seguras automáticamente si no se especifican.
    """
    postgres_password = body.postgres_password
    if not postgres_password:
        postgres_password = secrets.token_urlsafe(20)

    # Preparar acciones y configuraciones avanzadas
    actions = body.actions
    advanced_configs = {}
    if body.advanced:
        for k, v in body.advanced.items():
            advanced_configs[k] = v

    logger.info(f"🚀 [Setup Deploy] Postgres User={body.postgres_user}, DB={body.postgres_db}, Actions={actions}")

    # Ejecutar despliegue
    result = service.deploy_production_stack(
        postgres_password=postgres_password,
        postgres_user=body.postgres_user,
        postgres_db=body.postgres_db,
        actions=actions,
        advanced_configs=advanced_configs
    )

    if result.get("status") == "error":
        logger.error(f"❌ [Setup Deploy] Failed: {result.get('message')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Error durante el despliegue de Docker"),
        )

    # Forzar recarga en caliente de servicios en el proceso FastAPI
    try:
        from app.db.engine import reload_engine
        await reload_engine()
        
        # Intentar inicializar tablas Alembic/SQLModel programáticamente si Postgres está configurado
        from app.db.engine import create_db_and_tables
        await create_db_and_tables()
        logger.info("✅ [Setup Deploy] Tablas creadas/verificadas en la base de datos de producción.")
        
        # Recargar caché global si Redict está habilitado
        from app.utils.cache.manager import reload_cache_manager
        await reload_cache_manager()
    except Exception as e:
        logger.error(f"⚠️ [Setup Deploy] Error al sincronizar motores y tablas: {e}")

    return {
        "status": "success",
        "message": "Pila de infraestructura desplegada e integrada.",
        "details": result.get("details"),
        "postgres_password": postgres_password
    }


@router.post("/test-connection", response_model=dict)
async def test_setup_connection(
    body: TestConnectionRequest,
    session: AsyncSession = Depends(get_session),
    _guard: None = Depends(verify_system_not_setup)
):
    """
    Prueba la conexión a una base de datos o instancia de caché antes de confirmar.
    """
    provider = body.provider.lower()
    
    if provider == "sqlite":
        # SQLite local siempre funciona ya que se crea de forma local
        return {"status": "success", "message": "SQLite está disponible de forma local."}
        
    elif provider == "postgres":
        if not body.host or not body.user or not body.database:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host, usuario y base de datos son requeridos para PostgreSQL.",
            )
        
        port = body.port or 5432
        password = body.password or ""
        
        # Intentar conectar con SQLAlchemy
        from sqlalchemy import create_engine, text
        try:
            url = f"postgresql+psycopg://{body.user}:{password}@{body.host}:{port}/{body.database}"
            temp_engine = create_engine(url, connect_args={"connect_timeout": 3})
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "success", "message": "Conexión a PostgreSQL establecida con éxito."}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Fallo de conexión a PostgreSQL: {str(e)}"
            }
            
    elif provider == "redict":
        if not body.host:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host es requerido para Redict/Redis.",
            )
        
        port = body.port or 6379
        password = body.password or ""
        
        import redis.asyncio as redis
        try:
            auth = f":{password}@" if password else ""
            url = f"redis://{auth}{body.host}:{port}/0"
            client = redis.from_url(url, socket_connect_timeout=3.0)
            await client.ping()
            await client.aclose()
            return {"status": "success", "message": "Conexión a Redict establecida con éxito."}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Fallo de conexión a Redict: {str(e)}"
            }
            
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor de conexión no soportado: {body.provider}",
        )


@router.websocket("/ws/setup/logs/{container_name}")
async def websocket_setup_logs(
    websocket: WebSocket,
    container_name: str,
    service: InfrastructureService = Depends(get_infra_service),
    session: AsyncSession = Depends(get_session)
):
    """
    Streaming de logs de contenedores en vivo durante el setup inicial,
    protegido por la guardia verify_system_not_setup.
    """
    # Validar que el sistema aún no esté configurado
    result = await session.execute(select(User).limit(1))
    if result.first() is not None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info(f"🔌 WebSocket logs conectado para setup: {container_name}")
    
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
                logger.error(f"Error leyendo línea de log en setup: {e}")
                break
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error en WebSocket setup logs para {container_name}: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
