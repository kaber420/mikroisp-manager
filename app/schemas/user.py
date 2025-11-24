# app/schemas/user.py
"""
Pydantic schemas for FastAPI Users.
These schemas control what data is sent/received via the API.
"""
from typing import Optional
from fastapi_users import schemas
import uuid


class UserRead(schemas.BaseUser[uuid.UUID]):
    """
    Schema for reading user data (API responses).
    Includes all safe-to-expose user fields.
    """

    username: str
    role: str
    telegram_chat_id: Optional[str] = None
    receive_alerts: bool
    receive_announcements: bool
    disabled: bool


class UserCreate(schemas.BaseUserCreate):
    """
    Schema for creating new users.
    Requires email (FastAPI Users requirement) and username.
    """

    username: str
    email: str
    password: str
    role: str = "admin"
    telegram_chat_id: Optional[str] = None
    receive_alerts: bool = False
    receive_announcements: bool = False


class UserUpdate(schemas.BaseUserUpdate):
    """
    Schema for updating existing users.
    All fields are optional.
    """

    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    receive_alerts: Optional[bool] = None
    receive_announcements: Optional[bool] = None
    disabled: Optional[bool] = None
