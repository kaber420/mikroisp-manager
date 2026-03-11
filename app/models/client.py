# app/models/client.py
"""
Client model for ISP customer management.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


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

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    address: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    whatsapp_number: str | None = Field(default=None)
    email: str | None = Field(default=None)
    telegram_contact: str | None = Field(default=None)
    coordinates: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    service_status: str = Field(default="active", nullable=False)
    billing_day: int | None = Field(default=None)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    # Relationships (commented to avoid circular imports, can be enabled later)
    # services: List["ClientService"] = Relationship(back_populates="client")
    # payments: List["Payment"] = Relationship(back_populates="client")
