# app/services/plan_service.py
from typing import Any

from sqlmodel import Session, select

from ..models.plan import Plan
from ..models.router import Router
from .base_service import BaseCRUDService


class PlanService(BaseCRUDService[Plan]):
    """
    Service for Plan CRUD operations.
    Inherits generic methods from BaseCRUDService and adds plan-specific logic.
    """

    def __init__(self, session: Session):
        super().__init__(session, Plan)

    def get_all_plans(self) -> list[dict[str, Any]]:
        """
        Obtiene todos los planes e incluye el hostname del router asociado.
        Equivalente al JOIN que hacías en SQL crudo.
        """
        # Hacemos un join explícito para traer el nombre del router
        statement = select(Plan, Router.hostname).join(Router, Plan.router_host == Router.host)
        results = self.session.exec(statement).all()

        plans_list = []
        for plan, router_hostname in results:
            plan_dict = plan.model_dump()
            plan_dict["router_name"] = router_hostname or plan.router_host
            plans_list.append(plan_dict)

        return plans_list

    def get_plans_by_router(self, router_host: str) -> list[Plan]:
        """Obtiene los planes filtrados por host de router."""
        statement = select(Plan).where(Plan.router_host == router_host).order_by(Plan.name)
        return self.session.exec(statement).all()

    def create_plan(self, plan_data: dict[str, Any]) -> Plan:
        """
        Crea un nuevo plan en la base de datos.
        Overrides base to add uniqueness validation (router_host + name).
        """
        # Validar unicidad (router_host + name)
        existing = self.session.exec(
            select(Plan).where(
                Plan.router_host == plan_data["router_host"], Plan.name == plan_data["name"]
            )
        ).first()

        if existing:
            raise ValueError(f"El plan '{plan_data['name']}' ya existe en este router.")

        # Use base class create for the actual DB operation
        return super().create(plan_data)

    # Inherited from BaseCRUDService:
    # - get_by_id(id) -> Plan (replaces get_plan_by_id)
    # - delete(id) -> None (replaces delete_plan)
