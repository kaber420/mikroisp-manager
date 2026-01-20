"""
Shared Pydantic models for MikroTik provisioning requests/responses.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProvisionRequest(BaseModel):
    """Request model for provisioning a MikroTik device."""

    new_api_user: str = Field(..., min_length=1, max_length=64)
    new_api_password: str = Field(..., min_length=8, max_length=128)
    method: Literal["api", "ssh"] = "ssh"  # SSH is more secure, preferred default

    @field_validator("new_api_user")
    @classmethod
    def validate_username(cls, v):
        """Validate username format (alphanumeric, underscore, dash)."""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only "
                "alphanumeric characters, underscores, or dashes"
            )
        return v

    @field_validator("new_api_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Ensure password has minimum complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Optional: Add more complexity rules in the future
        return v


class ProvisionResponse(BaseModel):
    """Response model for provisioning operations."""

    status: str  # "success" | "error"
    message: str
    method_used: str | None = None
    warnings: list[str] | None = None  # Collect non-fatal warnings


class ProvisionStatus(BaseModel):
    """Model for checking provisioning status of a device."""

    host: str
    is_provisioned: bool
    vendor: str
    api_port: int
    api_ssl_port: int
    can_provision: bool  # True if vendor == "mikrotik" and not provisioned
    last_provision_attempt: datetime | None = None
    last_provision_error: str | None = None
