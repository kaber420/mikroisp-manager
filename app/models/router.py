from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class Router(SQLModel, table=True):
    __tablename__ = "routers"

    host: str = Field(primary_key=True, nullable=False)
    api_port: int = Field(default=8728)
    api_ssl_port: int = Field(default=8729)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)
    zona_id: Optional[int] = Field(default=None, foreign_key="zonas.id")
    is_enabled: bool = Field(default=True)
    hostname: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    firmware: Optional[str] = Field(default=None)
    last_status: Optional[str] = Field(default=None)
    last_checked: Optional[datetime] = Field(default=None)
    
    # Suspension Configuration
    # Options: "address_list", "queue_limit", "pppoe_disable", "none"
    suspension_type: Optional[str] = Field(default="address_list")
    # Custom name (will be prefixed with BL_ or WL_ automatically)
    address_list_name: Optional[str] = Field(default="morosos")
    # Options: "blacklist" (BL_), "whitelist" (WL_)
    address_list_strategy: Optional[str] = Field(default="blacklist")

    # Relationship
    # zona: Optional["Zona"] = Relationship(back_populates="routers")

