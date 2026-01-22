# app/api/plans/main.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session

from ...core.users import require_admin, require_technician
from ...db.engine_sync import get_sync_session
from ...models.user import User
from ...services.plan_service import PlanService

router = APIRouter()


# --- Modelos Pydantic para Request/Response ---
class PlanBase(BaseModel):
    name: str
    max_limit: str
    parent_queue: str | None = None
    comment: str | None = None
    router_host: str | None = None  # None = Universal Plan (works on all routers)
    price: float | None = 0.0
    plan_type: str | None = "simple_queue"  # "pppoe" or "simple_queue"
    profile_name: str | None = None  # For PPPoE: router profile name
    suspension_method: str | None = (
        "queue_limit"  # "pppoe_secret_disable", "address_list", "queue_limit"
    )
    address_list_strategy: str | None = "blacklist"
    address_list_name: str | None = "morosos"
    # Queue type configuration for different RouterOS versions
    v6_queue_type: str | None = "default-small"
    v7_queue_type: str | None = "cake-default"


class PlanCreate(PlanBase):
    pass


class PlanResponse(PlanBase):
    id: int
    router_name: str | None = None


# --- Inyección de Dependencia ---
def get_plan_service(session: Session = Depends(get_sync_session)) -> PlanService:
    return PlanService(session)


# --- Endpoints ---


@router.get("/plans", response_model=list[PlanResponse])
def get_all_plans(
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_technician),
):
    """Obtiene todos los planes de la base de datos."""
    return service.get_all_plans()


@router.get("/plans/router/{router_host}", response_model=list[PlanResponse])
def get_plans_by_router(
    router_host: str,
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_technician),
):
    plans = service.get_plans_by_router(router_host)
    # Mapeamos manualmente router_name si es necesario, o dejamos que sea null
    return [{**p.model_dump(), "router_name": None} for p in plans]


@router.get("/plans/for-service/{router_host}", response_model=list[PlanResponse])
def get_plans_for_service(
    router_host: str,
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene planes disponibles para crear servicios en un router.
    Incluye planes universales (router_host = NULL) + planes específicos del router.
    """
    return service.get_plans_for_service(router_host)


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan: PlanCreate,
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_admin),
):
    try:
        new_plan = service.create_plan(plan.model_dump())
        # Devolvemos el modelo, router_name será null por defecto en la respuesta inmediata
        return {**new_plan.model_dump(), "router_name": None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    request: Request,
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_admin),
):
    from ...core.audit import log_action

    service.delete(plan_id)
    log_action("DELETE", "plan", str(plan_id), user=current_user, request=request)
    return
