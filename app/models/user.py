# app/models/user.py
"""
User model for FastAPI Users with SQLModel.
Combines FastAPI Users base fields with custom ISP management fields.
"""

import uuid as uuid_pkg

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    User model combining FastAPI Users authentication fields with custom ISP fields.

    FastAPI Users provides minimal required fields, we add:
    - id: UUID (primary key)
    - email: str (unique, indexed)
    - hashed_password: str
    - is_active: bool (default True)
    - is_superuser: bool (default False)
    - is_verified: bool (default False)

    Custom fields for ISP management:
    - username: unique username for login
    - role: user role (admin, operator, etc.)
    - telegram_chat_id: for notifications
    - receive_alerts: opt-in for alert notifications
    - receive_announcements: opt-in for announcement notifications
    """

    __tablename__ = "users"

    # FastAPI Users required fields
    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
    email: str = Field(unique=True, index=True, nullable=False, max_length=320)
    hashed_password: str = Field(nullable=False, max_length=1024)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)

    # Custom fields
    username: str = Field(index=True, unique=True, nullable=False, max_length=100)
    role: str = Field(default="admin", max_length=50)
    telegram_chat_id: str | None = Field(default=None, max_length=100)
    receive_alerts: bool = Field(default=False)
    receive_device_down_alerts: bool = Field(default=False)
    receive_announcements: bool = Field(default=False)

    @property
    def disabled(self) -> bool:
        return not self.is_active
