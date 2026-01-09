# app/models/cpe.py
from typing import Optional
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel


class CPE(SQLModel, table=True):
    __tablename__ = "cpes"

    mac: str = Field(primary_key=True)
    hostname: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    firmware: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    is_enabled: bool = Field(default=True)
    status: str = Field(default="offline")  # 'active', 'offline', 'disabled'
    client_id: Optional[uuid.UUID] = Field(default=None, foreign_key="clients.id")
    service_id: Optional[int] = Field(default=None, foreign_key="client_services.id")
    first_seen: Optional[datetime] = Field(default=None)
    last_seen: Optional[datetime] = Field(default=None)


