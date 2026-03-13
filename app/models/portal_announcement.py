# app/models/portal_announcement.py
"""
Portal Announcement model for CMS.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PortalAnnouncement(SQLModel, table=True):
    """
    Portal Announcement model representing dynamic notices and offers for clients.

    Fields:
    - id: Auto-increment UUID primary key
    - title: Announcement title (e.g., "Mantenimiento", "Oferta de Verano")
    - content: Markdown content
    - image_url: Optional header image URL for promos
    - type: Category (offer, notice, holiday, alert)
    - priority: Importance level (1-5)
    - start_date: From when to show
    - end_date: Until when to show (optional)
    - is_active: Manual switch to turn off immediately
    - created_at: Timestamp of creation
    """

    __tablename__ = "portal_announcements"

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)  # Markdown supported
    image_url: str | None = Field(default=None)
    type: str = Field(default="notice", nullable=False)
    priority: int = Field(default=3, nullable=False)
    start_date: datetime | None = Field(default_factory=datetime.utcnow)
    end_date: datetime | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
