from typing import Optional
import uuid as uuid_pkg
from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class UserPreferenceBase(SQLModel):
    key: str = Field(index=True, max_length=100, description="Unique key for the preference/flag")
    value: str = Field(description="JSON or string value for the preference")
    status: str = Field(
        default="pending",
        max_length=50,
        description="Status of the flag (pending, dismissed, completed, always)"
    )


class UserPreference(UserPreferenceBase, table=True):
    __tablename__ = "user_preferences"

    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
    user_id: Optional[uuid_pkg.UUID] = Field(default=None, foreign_key="users.id", index=True)


class UserPreferenceCreate(UserPreferenceBase):
    user_id: Optional[uuid_pkg.UUID] = None


class UserPreferenceRead(UserPreferenceBase):
    id: uuid_pkg.UUID
    user_id: Optional[uuid_pkg.UUID]


class UserPreferenceUpdate(BaseModel):
    value: Optional[str] = None
    status: Optional[str] = None
