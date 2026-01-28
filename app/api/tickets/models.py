# app/api/tickets/models.py
import uuid as uuid_pkg
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class TicketCreate(BaseModel):
    client_id: uuid_pkg.UUID
    subject: str
    description: str
    priority: str = "normal"

class TicketUpdateStatus(BaseModel):
    status: str

class TicketReply(BaseModel):
    content: str
    media_url: Optional[str] = None

class TicketMessageRead(BaseModel):
    id: uuid_pkg.UUID
    sender_type: str
    sender_id: Optional[str]
    content: str
    created_at: datetime
    media_url: Optional[str]

class TicketRead(BaseModel):
    id: uuid_pkg.UUID
    ticket_id: int
    subject: str
    description: str
    status: str
    priority: str
    client_name: str
    assigned_tech_id: Optional[uuid_pkg.UUID]
    assigned_tech_username: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[TicketMessageRead] = []

class TicketListResponse(BaseModel):
    items: List[TicketRead]
    total: int
