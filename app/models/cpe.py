# app/models/cpe.py
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class CPE(SQLModel, table=True):
    __tablename__ = "cpes"

    mac: str = Field(primary_key=True)
    hostname: str | None = Field(default=None)
    model: str | None = Field(default=None)
    firmware: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    is_enabled: bool = Field(default=True)
    status: str = Field(default="offline")  # 'active', 'offline', 'disabled'
    client_id: uuid.UUID | None = Field(default=None, foreign_key="clients.id")
    service_id: int | None = Field(default=None, foreign_key="client_services.id")
    first_seen: datetime | None = Field(default=None)
    last_seen: datetime | None = Field(default=None)
