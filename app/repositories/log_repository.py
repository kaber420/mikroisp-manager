from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models.stats import EventLog


async def add_event_log(
    session: AsyncSession, host: str, device_type: str, event_type: str, message: str
):
    """
    Agrega un nuevo log de evento a la base de datos.
    """
    log = EventLog(
        device_host=host,
        device_type=device_type,
        event_type=event_type,
        message=message,
    )
    session.add(log)
    await session.commit()


async def get_event_logs_paginated(
    session: AsyncSession, host_filter: str = None, page: int = 1, page_size: int = 10
) -> list[EventLog]:
    """Obtiene logs con paginación."""
    offset = (page - 1) * page_size
    statement = select(EventLog).order_by(EventLog.timestamp.desc()).offset(offset).limit(page_size)

    if host_filter and host_filter != "all":
        statement = statement.where(EventLog.device_host == host_filter)

    result = await session.exec(statement)
    return list(result.all())


async def count_event_logs(session: AsyncSession, host_filter: str = None) -> int:
    """Cuenta el total de logs."""
    statement = select(func.count()).select_from(EventLog)

    if host_filter and host_filter != "all":
        statement = statement.where(EventLog.device_host == host_filter)

    result = await session.exec(statement)
    return result.one()
