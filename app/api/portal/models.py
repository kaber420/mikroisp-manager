# app/api/portal/models.py
import uuid as uuid_pkg
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class PortalClientRead(BaseModel):
    id: uuid_pkg.UUID
    name: str
    address: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    service_status: str
    billing_day: Optional[int]

class PortalTicketMessageRead(BaseModel):
    id: uuid_pkg.UUID
    sender_type: str
    sender_id: Optional[str]
    content: str
    created_at: datetime
    media_url: Optional[str]

class PortalTicketMessageCreate(BaseModel):
    content: str

class PortalTicketRead(BaseModel):
    id: uuid_pkg.UUID
    ticket_id: int
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    ticket_type: str
    assigned_tech_name: Optional[str] = None
    messages: List[PortalTicketMessageRead] = []

class PortalTicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "normal"
    ticket_type: str = "support"

class PortalPlanRead(BaseModel):
    id: int
    name: str
    max_limit: str
    price: float
    status: str
    pppoe_username: Optional[str]
    ip_address: Optional[str]

class PortalTicketListResponse(BaseModel):
    items: List[PortalTicketRead]
    total: int

class PortalVideoCallStart(BaseModel):
    """Request para iniciar videollamada."""
    subject: str
    description: str
    priority: str = "normal"

class PortalVideoCallResponse(BaseModel):
    """Respuesta con token de videollamada."""
    ticket_id: str
    token: str
    room: str
    server_url: str
    subject: str

class PortalSupportStatus(BaseModel):
    """Estado del área de soporte."""
    is_available: bool
    techs_online: int = 0
    pool_size: int = 0
    estimated_wait_minutes: int = 0
    message: str = ""
