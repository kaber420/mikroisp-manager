# app/models/service.py
"""
ClientService model for managing client internet services.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class ClientService(SQLModel, table=True):
    """Modelo que representa los servicios de internet asignados a los clientes."""

    __tablename__ = "client_services"

    id: int | None = Field(default=None, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", nullable=False, index=True)
    router_host: str = Field(foreign_key="routers.host", nullable=False)
    service_type: str = Field(default="pppoe", nullable=False)
    pppoe_username: str | None = Field(default=None, unique=True)
    router_secret_id: str | None = Field(default=None)
    profile_name: str | None = Field(default=None)
    suspension_method: str = Field(nullable=False)
    plan_id: int | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    address: str | None = Field(default=None)
    status: str = Field(default="active", nullable=False)
    billing_day: int | None = Field(default=None)
    notes: str | None = Field(default=None)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    # Relationships (commented to avoid circular imports)
    # client: Optional["Client"] = Relationship(back_populates="services")
    # router: Optional["Router"] = Relationship(back_populates="services")
