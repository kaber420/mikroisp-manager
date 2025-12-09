# app/models/client.py
"""
Client model for ISP customer management.
"""
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


class Client(SQLModel, table=True):
    """
    Client model representing ISP customers.
    
    Fields:
    - id: Auto-increment primary key
    - name: Client name (required)
    - address: Physical address
    - phone_number: Contact phone
    - whatsapp_number: WhatsApp contact
    - email: Email address
    - telegram_contact: Telegram username/ID
    - coordinates: GPS coordinates
    - notes: General notes
    - service_status: Current service status (active, suspended, etc.)
    - billing_day: Day of month for billing (1-31)
    - created_at: Registration timestamp
    """
    
    __tablename__ = "clients"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    address: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    whatsapp_number: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    telegram_contact: Optional[str] = Field(default=None)
    coordinates: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    service_status: str = Field(default="active", nullable=False)
    billing_day: Optional[int] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented to avoid circular imports, can be enabled later)
    # services: List["ClientService"] = Relationship(back_populates="client")
    # payments: List["Payment"] = Relationship(back_populates="client")
