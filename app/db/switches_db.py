# app/db/switches_db.py
"""
CRUD operations for Switches table using SQLModel and AsyncSession.
Follows the same patterns as router_db.py.
"""

import logging
from datetime import datetime
from typing import Any, Sequence

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from ..core.constants import DeviceStatus
from ..models.switch import Switch
from ..utils.security import decrypt_data, encrypt_data

logger = logging.getLogger(__name__)


# --- Funciones CRUD para la API ---


async def get_switch_by_host(session: AsyncSession, host: str) -> Switch | None:
    """Obtiene todos los datos de un switch por su host."""
    try:
        switch = await session.get(Switch, host)
        if not switch:
            return None

        # Return a copy with decrypted password
        switch_out = switch.model_copy()
        if switch_out.password:
            try:
                switch_out.password = decrypt_data(switch_out.password)
            except Exception as e:
                logger.error(f"Error decrypting password for switch {host}: {e}")
        return switch_out
    except Exception as e:
        logger.error(f"Error en switches_db.get_switch_by_host para {host}: {e}")
        return None


async def get_all_switches(session: AsyncSession) -> Sequence[Switch]:
    """Obtiene todos los switches de la base de datos."""
    try:
        stmt = select(Switch).order_by(Switch.host)
        result = await session.exec(stmt)
        switches = result.all()

        output = []
        for s in switches:
            s_out = s.model_copy()
            # Don't expose passwords in list view
            s_out.password = None
            output.append(s_out)
        return output
    except Exception as e:
        logger.error(f"Error en switches_db.get_all_switches: {e}")
        return []


async def create_switch_in_db(session: AsyncSession, switch_data: dict[str, Any]) -> Switch:
    """Inserta un nuevo switch en la base de datos."""
    # Prepare data explicitly to avoid side effects on input dict
    data = switch_data.copy()
    if "password" in data:
        data["password"] = encrypt_data(data["password"])

    switch = Switch(**data)
    session.add(switch)
    try:
        await session.commit()
        await session.refresh(switch)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Switch host (IP) '{switch_data.get('host')}' ya existe o error: {e}")

    # Return fetched version (decrypted)
    created = await get_switch_by_host(session, switch.host)
    if not created:
        raise ValueError("No se pudo recuperar el switch después de la creación.")
    return created


async def update_switch_in_db(session: AsyncSession, host: str, updates: dict[str, Any]) -> int:
    """
    Función genérica para actualizar cualquier campo de un switch.
    Devuelve el número de filas afectadas.
    """
    if not updates:
        return 0

    try:
        switch = await session.get(Switch, host)
        if not switch:
            return 0

        clean_updates = updates.copy()
        # Cifrar la contraseña si se está actualizando
        if "password" in clean_updates and clean_updates["password"]:
            clean_updates["password"] = encrypt_data(clean_updates["password"])

        # Update attributes
        for key, value in clean_updates.items():
            if hasattr(switch, key):
                setattr(switch, key, value)

        session.add(switch)
        await session.commit()
        await session.refresh(switch)
        return 1
    except Exception as e:
        logger.error(f"Error en switches_db.update_switch_in_db para {host}: {e}")
        await session.rollback()
        return 0


async def delete_switch_from_db(session: AsyncSession, host: str) -> int:
    """Elimina un switch de la base de datos. Devuelve el número de filas afectadas."""
    try:
        switch = await session.get(Switch, host)
        if not switch:
            return 0
        await session.delete(switch)
        await session.commit()
        return 1
    except Exception as e:
        logger.error(f"Error en switches_db.delete_switch_from_db para {host}: {e}")
        await session.rollback()
        return 0


# --- Funciones para el Monitor ---


async def get_switch_status(session: AsyncSession, host: str) -> str | None:
    """
    Obtiene el 'last_status' de un switch específico desde la base de datos.
    """
    try:
        switch = await session.get(Switch, host)
        return switch.last_status if switch else None
    except Exception:
        return None


async def update_switch_status(
    session: AsyncSession, host: str, status: str, data: dict[str, Any] | None = None
):
    """
    Actualiza el estado de un switch en la base de datos.
    Si el estado es 'online', también actualiza el hostname, modelo y firmware.
    """
    try:
        now = datetime.utcnow()
        update_data = {"last_status": status, "last_checked": now}

        if status == DeviceStatus.ONLINE and data:
            update_data["hostname"] = data.get("name")
            update_data["model"] = data.get("board-name")
            update_data["firmware"] = data.get("version")
            if data.get("mac_address"):
                update_data["mac_address"] = data.get("mac_address")

        await update_switch_in_db(session, host, update_data)

    except Exception as e:
        logger.error(f"Error en switches_db.update_switch_status para {host}: {e}")


async def get_enabled_switches_from_db(session: AsyncSession) -> Sequence[Switch]:
    """
    Obtiene la lista de Switches activos desde la BD.
    """
    try:
        stmt = select(Switch).where(Switch.is_enabled == True)
        result = await session.exec(stmt)
        switches = result.all()

        output = []
        for s in switches:
            s_out = s.model_copy()
            if s_out.password:
                try:
                    s_out.password = decrypt_data(s_out.password)
                except Exception:
                    pass
            output.append(s_out)
        return output
    except Exception as e:
        logger.error(f"No se pudo obtener la lista de Switches de la base de datos: {e}")
        return []
