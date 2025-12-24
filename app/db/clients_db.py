# app/db/clients_db.py
"""
Database access layer for Clients using SQLModel ORM.
Preserves original function signatures (Dict inputs/outputs) for backward compatibility.
"""
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, func, col, desc
from .engine_sync import sync_engine
from app.models import Client, ClientService
from app.models.cpe import CPE


def get_all_clients_with_cpe_count() -> List[Dict[str, Any]]:
    """Get all clients with their CPE count."""
    with Session(sync_engine) as session:
        # Build query with left join to count CPEs
        statement = (
            select(Client, func.count(CPE.mac).label("cpe_count"))
            .outerjoin(CPE, Client.id == CPE.client_id)
            .group_by(Client.id)
            .order_by(Client.name)
        )
        results = session.exec(statement).all()
        
        rows = []
        for client, cpe_count in results:
            client_dict = client.model_dump()
            client_dict["cpe_count"] = cpe_count
            rows.append(client_dict)
        
        return rows


def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    """Get a single client by ID."""
    with Session(sync_engine) as session:
        client = session.get(Client, client_id)
        if client:
            return client.model_dump()
        return None


def create_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new client."""
    with Session(sync_engine) as session:
        try:
            client = Client(
                name=client_data.get("name"),
                address=client_data.get("address"),
                phone_number=client_data.get("phone_number"),
                whatsapp_number=client_data.get("whatsapp_number"),
                email=client_data.get("email"),
                service_status=client_data.get("service_status", "active"),
                billing_day=client_data.get("billing_day"),
                notes=client_data.get("notes"),
            )
            session.add(client)
            session.commit()
            session.refresh(client)
            
            if not client.id:
                raise ValueError("No se pudo recuperar el cliente después de la creación.")
            
            result = client.model_dump()
            result["cpe_count"] = 0  # New client has no CPEs
            return result
        except Exception as e:
            session.rollback()
            raise e


def update_client(client_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing client."""
    with Session(sync_engine) as session:
        client = session.get(Client, client_id)
        if not client:
            return None
        
        # Update attributes dynamically
        for key, value in updates.items():
            if hasattr(client, key):
                setattr(client, key, value)
        
        session.add(client)
        session.commit()
        session.refresh(client)
        
        # Get CPE count for the response
        cpe_count_statement = select(func.count(CPE.mac)).where(CPE.client_id == client_id)
        cpe_count = session.exec(cpe_count_statement).one()
        
        result = client.model_dump()
        result["cpe_count"] = cpe_count
        return result


def delete_client(client_id: int) -> int:
    """Delete a client. Nullifies associated CPE client_id before deletion."""
    with Session(sync_engine) as session:
        try:
            client = session.get(Client, client_id)
            if not client:
                return 0
            
            # Nullify client_id for associated CPEs (matching original behavior)
            cpes_statement = select(CPE).where(CPE.client_id == client_id)
            cpes = session.exec(cpes_statement).all()
            for cpe in cpes:
                cpe.client_id = None
                session.add(cpe)
            
            session.delete(client)
            session.commit()
            return 1
        except Exception as e:
            session.rollback()
            raise e


def get_cpes_for_client(client_id: int) -> List[Dict[str, Any]]:
    """Get CPEs assigned to a specific client."""
    with Session(sync_engine) as session:
        statement = select(CPE.mac, CPE.hostname, CPE.ip_address).where(
            CPE.client_id == client_id
        )
        results = session.exec(statement).all()
        
        # Convert to list of dicts matching original column structure
        return [
            {"mac": row.mac, "hostname": row.hostname, "ip_address": row.ip_address}
            for row in results
        ]


# --- Service Functions ---


def get_client_service_by_id(service_id: int) -> Optional[Dict[str, Any]]:
    """Get a client service by ID."""
    with Session(sync_engine) as session:
        service = session.get(ClientService, service_id)
        if service:
            return service.model_dump()
        return None


def get_services_for_client(client_id: int) -> List[Dict[str, Any]]:
    """Get all services for a specific client."""
    with Session(sync_engine) as session:
        statement = (
            select(ClientService)
            .where(ClientService.client_id == client_id)
            .order_by(desc(ClientService.created_at))
        )
        results = session.exec(statement).all()
        return [service.model_dump() for service in results]


def create_client_service(client_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new client service."""
    with Session(sync_engine) as session:
        try:
            service = ClientService(
                client_id=client_id,
                router_host=data["router_host"],
                service_type=data["service_type"],
                pppoe_username=data.get("pppoe_username"),
                router_secret_id=data.get("router_secret_id"),
                profile_name=data.get("profile_name"),
                suspension_method=data["suspension_method"],
                plan_id=data.get("plan_id"),
                ip_address=data.get("ip_address"),
            )
            session.add(service)
            session.commit()
            session.refresh(service)
            
            if not service.id:
                raise ValueError("No se pudo recuperar el servicio después de la creación.")
            
            return service.model_dump()
        except Exception as e:
            session.rollback()
            raise ValueError(str(e))


def get_active_clients_by_billing_day(day: int) -> List[Dict[str, Any]]:
    """Get active clients with a specific billing day."""
    with Session(sync_engine) as session:
        statement = select(Client.id, Client.name).where(
            Client.service_status == "active",
            Client.billing_day == day
        )
        results = session.exec(statement).all()
        return [{"id": row.id, "name": row.name} for row in results]
