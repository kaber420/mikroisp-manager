# app/schemas/portal_announcement.py
"""
Pydantic schemas for Portal Announcements.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PortalAnnouncementBase(BaseModel):
    title: str = Field(..., description="Title of the announcement")
    content: str = Field(..., description="Markdown content")
    image_url: Optional[str] = Field(None, description="Optional image URL")
    type: str = Field("notice", description="Category: offer, notice, holiday, alert")
    priority: int = Field(3, description="Importance level 1-5")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True


class PortalAnnouncementCreate(PortalAnnouncementBase):
    pass


class PortalAnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class PortalAnnouncementRead(PortalAnnouncementBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
