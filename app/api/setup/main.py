# app/api/setup/main.py
"""
First-run wizard API for creating the initial admin user via Web UI.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.users import get_user_manager, UserManager
from app.db.engine import get_session
from app.models.user import User
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Setup"])


class SetupRequest(BaseModel):
    """Request body for creating the first admin user."""
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El usuario no puede estar vacío.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        return v


async def _is_system_setup(session: AsyncSession) -> bool:
    """Check if any user exists in the database."""
    result = await session.exec(select(User).limit(1))
    return result.first() is not None


@router.post("/setup")
async def create_first_admin(
    request_body: SetupRequest,
    session: AsyncSession = Depends(get_session),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Create the first admin user.
    This endpoint is only active if no users exist.
    """
    if await _is_system_setup(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El sistema ya está configurado. No puedes crear más usuarios desde aquí.",
        )

    try:
        # Create user with FastAPI Users' UserManager
        user_create = UserCreate(
            email=request_body.email,
            username=request_body.username,
            password=request_body.password,
            role="admin",
            is_superuser=True,
            is_active=True,
            is_verified=True,
        )
        await user_manager.create(user_create)
        logger.info(f"🚀 [Setup] First admin user created: {request_body.username}")
        return {"status": "ok", "message": "Administrador creado exitosamente."}
    except Exception as e:
        logger.error(f"❌ [Setup] Failed to create admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el usuario: {e}",
        )
