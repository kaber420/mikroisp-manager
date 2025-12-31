# app/models/service.py
"""
ClientService model for managing client internet services.
"""
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


class ClientService(SQLModel, table=True):
    """Modelo que representa los servicios de internet asignados a los clientes."""
    
    __tablename__ = "client_services"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", nullable=False, index=True)
    router_host: str = Field(foreign_key="routers.host", nullable=False)
    service_type: str = Field(default="pppoe", nullable=False)
    pppoe_username: Optional[str] = Field(default=None, unique=True)
    router_secret_id: Optional[str] = Field(default=None)
    profile_name: Optional[str] = Field(default=None)
    suspension_method: str = Field(nullable=False)
    plan_id: Optional[int] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    status: str = Field(default="active", nullable=False)
    billing_day: Optional[int] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented to avoid circular imports)
    # client: Optional["Client"] = Relationship(back_populates="services")
    # router: Optional["Router"] = Relationship(back_populates="services")
