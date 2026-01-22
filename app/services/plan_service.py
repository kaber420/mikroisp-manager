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
        Usa LEFT JOIN para incluir planes universales (router_host = NULL).
        """
        from sqlmodel import or_

        # LEFT JOIN para incluir planes universales
        statement = select(Plan, Router.hostname).outerjoin(
            Router, Plan.router_host == Router.host
        ).order_by(Plan.name)
        results = self.session.exec(statement).all()

        plans_list = []
        for plan, router_hostname in results:
            plan_dict = plan.model_dump()
            if plan.router_host is None:
                plan_dict["router_name"] = "Universal"
            else:
                plan_dict["router_name"] = router_hostname or plan.router_host
            plans_list.append(plan_dict)

        return plans_list

    def get_plans_by_router(self, router_host: str) -> list[Plan]:
        """Obtiene los planes filtrados por host de router específico."""
        statement = select(Plan).where(Plan.router_host == router_host).order_by(Plan.name)
        return self.session.exec(statement).all()

    def get_plans_for_service(self, router_host: str) -> list[dict[str, Any]]:
        """
        Obtiene planes para creación de servicios.
        Incluye planes universales (router_host IS NULL) + planes específicos del router.
        """
        from sqlmodel import or_

        statement = select(Plan, Router.hostname).outerjoin(
            Router, Plan.router_host == Router.host
        ).where(
            or_(Plan.router_host.is_(None), Plan.router_host == router_host)
        ).order_by(Plan.name)

        results = self.session.exec(statement).all()

        plans_list = []
        for plan, router_hostname in results:
            plan_dict = plan.model_dump()
            if plan.router_host is None:
                plan_dict["router_name"] = "Universal"
            else:
                plan_dict["router_name"] = router_hostname or plan.router_host
            plans_list.append(plan_dict)

        return plans_list

    def create_plan(self, plan_data: dict[str, Any]) -> Plan:
        """
        Crea un nuevo plan en la base de datos.
        Overrides base to add uniqueness validation.
        For universal plans: name must be unique among universal plans.
        For router-specific plans: (router_host + name) must be unique.
        """
        from sqlmodel import and_

        router_host = plan_data.get("router_host")
        plan_name = plan_data["name"]

        if router_host is None:
            # Universal plan: check name is unique among universal plans
            existing = self.session.exec(
                select(Plan).where(
                    and_(Plan.router_host.is_(None), Plan.name == plan_name)
                )
            ).first()
            if existing:
                raise ValueError(f"El plan universal '{plan_name}' ya existe.")
        else:
            # Router-specific plan: check uniqueness for this router
            existing = self.session.exec(
                select(Plan).where(
                    and_(Plan.router_host == router_host, Plan.name == plan_name)
                )
            ).first()
            if existing:
                raise ValueError(f"El plan '{plan_name}' ya existe en este router.")

        # Use base class create for the actual DB operation
        return super().create(plan_data)

    # Inherited from BaseCRUDService:
    # - get_by_id(id) -> Plan (replaces get_plan_by_id)
    # - delete(id) -> None (replaces delete_plan)

