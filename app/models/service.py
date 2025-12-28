# app/models/service.py
"""
ClientService model for managing client internet services.
"""
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


class ClientService(SQLModel, table=True):
    """
    ClientService model representing internet services assigned to clients.
    
    Fields:
    - id: Auto-increment primary key
    - client_id: Foreign key to clients table (required)
    - router_host: Foreign key to routers table (required)
    - service_type: Type of service (pppoe, simple_queue, etc.)
    - pppoe_username: PPPoE username (unique, optional)
    - router_secret_id: MikroTik secret ID (optional)
    - profile_name: MikroTik profile name (optional)
    - suspension_method: How to suspend service (required)
    - plan_id: Foreign key to plans table (optional)
    - ip_address: Assigned IP address (optional)
    - created_at: Service creation timestamp
    """
    
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
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented to avoid circular imports)
    # client: Optional["Client"] = Relationship(back_populates="services")
    # router: Optional["Router"] = Relationship(back_populates="services")
