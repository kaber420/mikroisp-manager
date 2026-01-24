# app/api/aps/dependencies.py
"""Shared dependencies for AP API endpoints."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.engine import get_session
from ...services.ap_service import APService


async def get_ap_service(session: AsyncSession = Depends(get_session)) -> APService:
    """Dependency injector for APService."""
    return APService(session)
