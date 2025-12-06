# app/models/plan.py
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    router_host: str = Field(foreign_key="routers.host", nullable=False, index=True)
    name: str = Field(nullable=False)
    max_limit: str = Field(nullable=False)  # ej. "10M/10M"
    parent_queue: Optional[str] = Field(default="none")
    comment: Optional[str] = Field(default=None)

    # Relaciones (Opcional, ayuda a obtener datos del router automáticamente)
    # router: Optional["Router"] = Relationship(back_populates="plans")
