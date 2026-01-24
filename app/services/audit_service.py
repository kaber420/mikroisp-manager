from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_audit_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        action_filter: Optional[str] = None,
        username_filter: Optional[str] = None,
    ) -> List[AuditLog]:
        """
        Retrieves audit logs with pagination and optional filters using AsyncSession.
        """
        offset = (page - 1) * page_size
        statement = select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size)

        if action_filter and action_filter != "all":
            statement = statement.where(AuditLog.action == action_filter.upper())

        if username_filter and username_filter != "all":
            statement = statement.where(AuditLog.username == username_filter)

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_audit_logs(
        self,
        action_filter: Optional[str] = None,
        username_filter: Optional[str] = None,
    ) -> int:
        """
        Counts total audit logs matching the given filters.
        """
        statement = select(func.count()).select_from(AuditLog)

        if action_filter and action_filter != "all":
            statement = statement.where(AuditLog.action == action_filter.upper())

        if username_filter and username_filter != "all":
            statement = statement.where(AuditLog.username == username_filter)

        result = await self.session.execute(statement)
        return result.scalar_one() or 0

    async def get_distinct_usernames(self) -> List[str]:
        """Returns a list of distinct usernames who have audit entries."""
        statement = select(AuditLog.username).distinct().order_by(AuditLog.username)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_distinct_actions(self) -> List[str]:
        """Returns a list of distinct action types in the audit log."""
        statement = select(AuditLog.action).distinct().order_by(AuditLog.action)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
