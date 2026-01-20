# app/schemas/user.py
"""
Pydantic schemas for FastAPI Users.
These schemas control what data is sent/received via the API.
"""

import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """
    Schema for reading user data (API responses).
    Includes all safe-to-expose user fields.
    """

    email: str
    username: str
    role: str
    telegram_chat_id: str | None = None
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
    telegram_chat_id: str | None = None
    receive_alerts: bool = False
    receive_announcements: bool = False


class UserUpdate(schemas.BaseUserUpdate):
    """
    Schema for updating existing users.
    All fields are optional.
    """

    username: str | None = None
    email: str | None = None
    password: str | None = None
    role: str | None = None
    telegram_chat_id: str | None = None
    receive_alerts: bool | None = None
    receive_announcements: bool | None = None
    disabled: bool | None = None
