from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class AP(SQLModel, table=True):
    __tablename__ = "aps"

    host: str = Field(primary_key=True, nullable=False)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)
    zona_id: Optional[int] = Field(default=None, foreign_key="zonas.id")
    is_enabled: bool = Field(default=True)
    monitor_interval: Optional[int] = Field(default=None)
    mac: Optional[str] = Field(default=None)
    hostname: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    firmware: Optional[str] = Field(default=None)
    last_status: Optional[str] = Field(default=None)
    first_seen: Optional[datetime] = Field(default=None)
    last_seen: Optional[datetime] = Field(default=None)
    last_checked: Optional[datetime] = Field(default=None)
    
    # Multi-vendor support
    # vendor: "ubiquiti" (AirMAX), "mikrotik" (RouterOS wireless)
    vendor: Optional[str] = Field(default="ubiquiti")
    # role: "access_point", "switch" (for future expansion)
    role: Optional[str] = Field(default="access_point")
    # api_port: custom port for API connections (default 443 for Ubiquiti, 8729 for MikroTik SSL)
    api_port: Optional[int] = Field(default=443)
    
    # Provisioning fields (for MikroTik APs)
    api_ssl_port: Optional[int] = Field(default=8729)
    is_provisioned: bool = Field(default=False)
    last_provision_attempt: Optional[datetime] = Field(default=None)
    last_provision_error: Optional[str] = Field(default=None)

    # Relationship
    # zona: Optional["Zona"] = Relationship(back_populates="aps")
