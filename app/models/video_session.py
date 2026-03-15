import uuid as uuid_pkg
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class VideoSessionLog(SQLModel, table=True):
    """
    Log of a video session for a ticket.
    Used for analytics and SLA tracking.
    """
    __tablename__ = "video_session_logs"

    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    ticket_id: uuid_pkg.UUID = Field(foreign_key="tickets.id", index=True)
    tech_id: Optional[uuid_pkg.UUID] = Field(default=None, foreign_key="users.id", index=True)
    
    room_name: str = Field(nullable=False, index=True)
    
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(default=None)
    
    wait_time_seconds: Optional[int] = Field(default=None)
    duration_seconds: Optional[int] = Field(default=None)
