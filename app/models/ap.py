from datetime import datetime

from sqlmodel import Field, SQLModel


class AP(SQLModel, table=True):
    __tablename__ = "aps"

    host: str = Field(primary_key=True, nullable=False)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)
    zona_id: int | None = Field(default=None, foreign_key="zonas.id")
    is_enabled: bool = Field(default=True)
    monitor_interval: int | None = Field(default=None)
    mac: str | None = Field(default=None)
    hostname: str | None = Field(default=None)
    model: str | None = Field(default=None)
    firmware: str | None = Field(default=None)
    last_status: str | None = Field(default=None)
    first_seen: datetime | None = Field(default=None)
    last_seen: datetime | None = Field(default=None)
    last_checked: datetime | None = Field(default=None)

    # Multi-vendor support
    # vendor: "ubiquiti" (AirMAX), "mikrotik" (RouterOS wireless)
    vendor: str | None = Field(default="ubiquiti")
    # role: "access_point", "switch" (for future expansion)
    role: str | None = Field(default="access_point")
    # api_port: custom port for API connections (default 443 for Ubiquiti, 8729 for MikroTik SSL)
    api_port: int | None = Field(default=443)

    # Provisioning fields (for MikroTik APs)
    api_ssl_port: int | None = Field(default=8729)
    is_provisioned: bool = Field(default=False)
    last_provision_attempt: datetime | None = Field(default=None)
    last_provision_error: str | None = Field(default=None)

    # Relationship
    # zona: Optional["Zona"] = Relationship(back_populates="aps")
