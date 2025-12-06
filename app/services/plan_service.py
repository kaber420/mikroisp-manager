# app/services/plan_service.py
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from fastapi import HTTPException

from ..models.plan import Plan
from ..models.router import Router

class PlanService:
    def __init__(self, session: Session):
        self.session = session

    def get_all_plans(self) -> List[Dict[str, Any]]:
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

    def get_plans_by_router(self, router_host: str) -> List[Plan]:
        """Obtiene los planes filtrados por host de router."""
        statement = select(Plan).where(Plan.router_host == router_host).order_by(Plan.name)
        return self.session.exec(statement).all()

    def create_plan(self, plan_data: Dict[str, Any]) -> Plan:
        """Crea un nuevo plan en la base de datos."""
        # Validar unicidad (router_host + name)
        existing = self.session.exec(
            select(Plan).where(
                Plan.router_host == plan_data["router_host"],
                Plan.name == plan_data["name"]
            )
        ).first()
        
        if existing:
            raise ValueError(f"El plan '{plan_data['name']}' ya existe en este router.")

        try:
            new_plan = Plan(**plan_data)
            self.session.add(new_plan)
            self.session.commit()
            self.session.refresh(new_plan)
            return new_plan
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creando plan: {str(e)}")

    def get_plan_by_id(self, plan_id: int) -> Plan:
        plan = self.session.get(Plan, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        return plan

    def delete_plan(self, plan_id: int):
        plan = self.session.get(Plan, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        self.session.delete(plan)
        self.session.commit()
