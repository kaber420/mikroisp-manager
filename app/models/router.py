from datetime import datetime

from sqlmodel import Field, SQLModel


class Router(SQLModel, table=True):
    __tablename__ = "routers"

    host: str = Field(primary_key=True, nullable=False)
    api_port: int = Field(default=8728)
    api_ssl_port: int = Field(default=8729)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)
    zona_id: int | None = Field(default=None, foreign_key="zonas.id")
    is_enabled: bool = Field(default=True)
    hostname: str | None = Field(default=None)
    model: str | None = Field(default=None)
    firmware: str | None = Field(default=None)
    last_status: str | None = Field(default=None)
    last_checked: datetime | None = Field(default=None)

    # Suspension Configuration
    # Options: "address_list", "queue_limit", "pppoe_disable", "none"
    suspension_type: str | None = Field(default="address_list")
    # Custom name (will be prefixed with BL_ or WL_ automatically)
    address_list_name: str | None = Field(default="morosos")
    # Options: "blacklist" (BL_), "whitelist" (WL_)
    address_list_strategy: str | None = Field(default="blacklist")

    # WAN Interface for traffic monitoring
    wan_interface: str | None = Field(default=None)

    # Provisioning status (True after successful secure provisioning)
    is_provisioned: bool = Field(default=False)

    # Relationship
    # zona: Optional["Zona"] = Relationship(back_populates="routers")
