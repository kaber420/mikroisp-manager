import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...core.users import require_admin
from ...models.user import User
from ...services.core.infrastructure_service import InfrastructureService
from ...core.audit import log_action

router = APIRouter()


def get_infra_service():
    return InfrastructureService()


class ServiceAction(BaseModel):
    postgres: str = "create"   # "create" | "reuse" | "skip"
    redict: str = "create"     # "create" | "reuse" | "skip"


class DeployRequest(BaseModel):
    postgres_password: Optional[str] = None
    actions: ServiceAction = ServiceAction()


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
    actions.postgres / actions.redict: "create" | "reuse" | "skip"
    Requiere SuperAdmin.
    """
    postgres_password = body.postgres_password or secrets.token_urlsafe(20)

    result = service.deploy_production_stack(
        postgres_password=postgres_password,
        actions=body.actions.model_dump(),
    )

    if result.get("status") == "error":
        log_action(
            action="INFRA_DEPLOY",
            resource_type="system",
            resource_id="docker",
            user=current_user,
            status="failure",
            details={"error": result.get("message")},
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
    )

    return {
        "message": "Stack de Producción procesado.",
        "details": result.get("details"),
        "postgres_password": result.get("postgres_password")
    }
