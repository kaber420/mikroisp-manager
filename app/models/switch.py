# app/models/switch.py
from datetime import datetime

from sqlmodel import Field, SQLModel


class Switch(SQLModel, table=True):
    __tablename__ = "switches"

    host: str = Field(primary_key=True, nullable=False)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)
    zona_id: int | None = Field(default=None, foreign_key="zonas.id")
    api_port: int = Field(default=8728)
    api_ssl_port: int = Field(default=8729)
    is_enabled: bool = Field(default=True)
    is_provisioned: bool = Field(default=False)
    hostname: str | None = Field(default=None)
    model: str | None = Field(default=None)
    firmware: str | None = Field(default=None)
    mac_address: str | None = Field(default=None)
    location: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    last_status: str | None = Field(default=None)
    last_checked: datetime | None = Field(default=None)
