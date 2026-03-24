# app/models/payment.py
"""
Payment model for client payment tracking.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class Payment(SQLModel, table=True):
    """
    Payment model representing client payments.

    Fields:
    - id: Auto-increment primary key
    - client_id: Foreign key to clients table (required)
    - monto: Payment amount (required)
    - fecha_pago: Payment date timestamp
    - mes_correspondiente: Billing cycle (format: 'YYYY-MM', required)
    - metodo_pago: Payment method (cash, transfer, etc.)
    - notas: Additional notes
    """

    __tablename__ = "pagos"

    id: int | None = Field(default=None, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", nullable=False, index=True)
    monto: float = Field(nullable=False)
    fecha_pago: datetime | None = Field(default_factory=datetime.utcnow)
    mes_correspondiente: str = Field(nullable=False)
    metodo_pago: str | None = Field(default=None)
    notas: str | None = Field(default=None)

    # Relationships (commented to avoid circular imports)
    # client: Optional["Client"] = Relationship(back_populates="payments")
