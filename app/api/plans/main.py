# app/api/plans/main.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session

from ...core.users import require_admin, require_technician
from ...models.user import User
from ...db.engine_sync import get_sync_session
from ...services.plan_service import PlanService
from ...models.plan import Plan as PlanModel  # Importamos el modelo de DB

router = APIRouter()

# --- Modelos Pydantic para Request/Response ---
class PlanBase(BaseModel):
    name: str
    max_limit: str
    parent_queue: Optional[str] = None
    comment: Optional[str] = None
    router_host: str

class PlanCreate(PlanBase):
    pass

class PlanResponse(PlanBase):
    id: int
    router_name: Optional[str] = None 

# --- Inyección de Dependencia ---
def get_plan_service(session: Session = Depends(get_sync_session)) -> PlanService:
    return PlanService(session)

# --- Endpoints ---

@router.get("/plans", response_model=List[PlanResponse])
def get_all_plans(
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_technician)
):
    """Obtiene todos los planes de la base de datos."""
    return service.get_all_plans()

@router.get("/plans/router/{router_host}", response_model=List[PlanResponse])
def get_plans_by_router(
    router_host: str, 
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_technician)
):
    plans = service.get_plans_by_router(router_host)
    # Mapeamos manualmente router_name si es necesario, o dejamos que sea null
    return [
        {**p.model_dump(), "router_name": None} for p in plans
    ]

@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan: PlanCreate, 
    service: PlanService = Depends(get_plan_service),
    current_user: User = Depends(require_admin)
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
    current_user: User = Depends(require_admin)
):
    from ...core.audit import log_action
    service.delete_plan(plan_id)
    log_action("DELETE", "plan", str(plan_id), user=current_user, request=request)
    return
