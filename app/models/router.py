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

    # Relationship
    # zona: Optional["Zona"] = Relationship(back_populates="routers")
