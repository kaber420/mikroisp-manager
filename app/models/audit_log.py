from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str
    username: str
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    status: str = Field(default="success")
    details: Optional[str] = None  # JSON string
