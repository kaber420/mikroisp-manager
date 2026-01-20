# app/models/plan.py

from sqlmodel import Field, SQLModel


class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: int | None = Field(default=None, primary_key=True)
    router_host: str = Field(foreign_key="routers.host", nullable=False, index=True)
    name: str = Field(nullable=False)
    max_limit: str = Field(nullable=False)  # ej. "10M/10M"
    parent_queue: str | None = Field(default="none")
    comment: str | None = Field(default=None)
    price: float = Field(default=0.0)

    # Plan type: "pppoe" or "simple_queue"
    plan_type: str = Field(default="simple_queue")

    # For PPPoE: name of the profile in the router
    profile_name: str | None = Field(default=None)

    # Suspension method: "pppoe_secret_disable", "address_list", "queue_limit"
    suspension_method: str = Field(default="queue_limit")

    # Suspension Configuration (Address List)
    # Options: "blacklist" or "whitelist"
    address_list_strategy: str | None = Field(default="blacklist")
    # Custom list name (e.g. "morosos", "authorized_users")
    address_list_name: str | None = Field(default="morosos")

    # Relaciones (Opcional, ayuda a obtener datos del router automáticamente)
    # router: Optional["Router"] = Relationship(back_populates="plans")
