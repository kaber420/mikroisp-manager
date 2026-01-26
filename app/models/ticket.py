# app/models/ticket.py
"""
Ticket models for the unified support system.
Integrates directly with inventory.sqlite.
"""

import uuid as uuid_pkg
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

# Forward reference for Client if needed, but for now we just store client_id
# from app.models.client import Client

class Ticket(SQLModel, table=True):
    """
    Represents a support ticket.
    Stored in the main inventory database.
    """
    __tablename__ = "tickets"

    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    ticket_id: int = Field(default=0, sa_column_kwargs={"autoincrement": True}) # Easy ID for humans (optional concept, or just rely on UUID/shortID)
    # Note: SQLModel doesn't support auto-increment on non-primary keys easily in all dialects without custom SA schema. 
    # For simplicity in SQLite, we might stick to UUID or a separate counter. 
    # Let's use a string ID or just rely on UUID for the backend and a generated number logic if strictly needed.
    # Re-reading the plan: "El bot responde con un ID de ticket".
    # Let's keep it simple: Use a short string or rely on the primary key if it was int. 
    # Since we are using UUIDs for primary keys in this project (seen in User and Client), 
    # we might want a human-readable ID. For now, let's just make a 'display_id' or similar manually or use the UUID prefix.
    
    client_id: uuid_pkg.UUID = Field(foreign_key="clients.id", index=True)
    status: str = Field(default="open", index=True)  # open, pending, resolved, closed
    priority: str = Field(default="normal")
    subject: str = Field(nullable=False)
    description: str = Field(nullable=False)
    
    assigned_tech_id: Optional[uuid_pkg.UUID] = Field(default=None, foreign_key="users.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # We can add relationships here if we want to navigate object.messages
    messages: List["TicketMessage"] = Relationship(back_populates="ticket")


class TicketMessage(SQLModel, table=True):
    """
    Individual messages within a ticket (chat history).
    """
    __tablename__ = "ticket_messages"

    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    ticket_id: uuid_pkg.UUID = Field(foreign_key="tickets.id", index=True)
    
    sender_type: str = Field(nullable=False) # 'client', 'tech', 'system'
    sender_id: Optional[str] = Field(default=None) # User UUID or Client UUID or TelegramID
    
    content: str = Field(nullable=False)
    media_url: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    ticket: Ticket = Relationship(back_populates="messages")
