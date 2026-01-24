
import logging
from datetime import datetime
from typing import Any, Sequence

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from ..core.constants import DeviceStatus
from ..models.router import Router
from ..models.zona import Zona
from ..utils.security import decrypt_data, encrypt_data


async def get_router_by_host(session: AsyncSession, host: str) -> Router | None:
    """Obtiene todos los datos de un router por su host."""
    try:
        router = await session.get(Router, host)
        if not router:
            return None

        # Return a copy with decrypted password
        router_out = router.model_copy()
        if router_out.password:
            try:
                router_out.password = decrypt_data(router_out.password)
            except Exception as e:
                logging.error(f"Error decrypting password for router {host}: {e}")
        return router_out
    except Exception as e:
        logging.error(f"Error en router_db.get_router_by_host para {host}: {e}")
        return None


async def get_all_routers(session: AsyncSession) -> Sequence[Router]:
    """Obtiene todos los routers de la base de datos."""
    try:
        stmt = select(Router).order_by(Router.host)
        result = await session.exec(stmt)
        routers = result.all()

        output = []
        for r in routers:
            r_out = r.model_copy()
            if r_out.password:
                try:
                    r_out.password = decrypt_data(r_out.password)
                except Exception:
                    pass
            output.append(r_out)
        return output
    except Exception as e:
        logging.error(f"Error en router_db.get_all_routers: {e}")
        return []


async def create_router_in_db(session: AsyncSession, router_data: dict[str, Any]) -> Router:
    """Inserta un nuevo router en la base de datos."""
    # Prepare data explicitly to avoid side effects on input dict
    data = router_data.copy()
    if "password" in data:
        data["password"] = encrypt_data(data["password"])

    router = Router(**data)
    session.add(router)
    try:
        await session.commit()
        await session.refresh(router)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Router host (IP) '{router_data.get('host')}' ya existe o error: {e}")

    # Return fetched version (decrypted)
    created = await get_router_by_host(session, router.host)
    if not created:
        raise ValueError("No se pudo recuperar el router después de la creación.")
    return created


async def update_router_in_db(session: AsyncSession, host: str, updates: dict[str, Any]) -> int:
    """
    Función genérica para actualizar cualquier campo de un router.
    Devuelve el número de filas afectadas.
    """
    if not updates:
        return 0

    try:
        router = await session.get(Router, host)
        if not router:
            return 0

        clean_updates = updates.copy()
        # Cifrar la contraseña si se está actualizando
        if "password" in clean_updates and clean_updates["password"]:
            clean_updates["password"] = encrypt_data(clean_updates["password"])

        # Update attributes
        for key, value in clean_updates.items():
            if hasattr(router, key):
                setattr(router, key, value)

        session.add(router)
        await session.commit()
        await session.refresh(router)
        return 1
    except Exception as e:
        logging.error(f"Error en router_db.update_router_in_db para {host}: {e}")
        await session.rollback()
        return 0


async def delete_router_from_db(session: AsyncSession, host: str) -> int:
    """Elimina un router de la base de datos. Devuelve el número de filas afectadas."""
    try:
        router = await session.get(Router, host)
        if not router:
            return 0
        await session.delete(router)
        await session.commit()
        return 1
    except Exception as e:
        logging.error(f"Error en router_db.delete_router_from_db para {host}: {e}")
        await session.rollback()
        return 0


async def get_router_status(session: AsyncSession, host: str) -> str | None:
    """
    Obtiene el 'last_status' de un router específico.
    """
    try:
        router = await session.get(Router, host)
        return router.last_status if router else None
    except Exception:
        return None


async def update_router_status(session: AsyncSession, host: str, status: str, data: dict[str, Any] | None = None):
    """
    Actualiza el estado de un router en la base de datos.
    Si el estado es 'online', también actualiza el hostname, modelo y firmware.
    """
    try:
        now = datetime.utcnow()
        update_data = {"last_status": status, "last_checked": now}

        if status == DeviceStatus.ONLINE and data:
            update_data["hostname"] = data.get("name")
            update_data["model"] = data.get("board-name")
            update_data["firmware"] = data.get("version")

        await update_router_in_db(session, host, update_data)

    except Exception as e:
        logging.error(f"Error en router_db.update_router_status para {host}: {e}")


async def get_enabled_routers_from_db(session: AsyncSession) -> Sequence[Router]:
    """
    Obtiene la lista de Routers activos y aprovisionados desde la BD.
    """
    try:
        stmt = select(Router).where(Router.is_enabled == True, Router.is_provisioned == True)
        result = await session.exec(stmt)
        routers = result.all()

        output = []
        for r in routers:
            r_out = r.model_copy()
            if r_out.password:
                try:
                    r_out.password = decrypt_data(r_out.password)
                except Exception:
                    pass
            output.append(r_out)
        return output
    except Exception as e:
        logging.error(f"No se pudo obtener la lista de Routers de la base de datos: {e}")
        return []


async def get_routers_for_backup(session: AsyncSession) -> list[dict[str, Any]]:
    """
    Obtiene routers activos con datos necesarios para backup (incluye nombre de zona).
    """
    routers = []
    try:
        # Join with Zona to get zona_nombre
        stmt = (
            select(Router, Zona.nombre)
            .outerjoin(Zona, Router.zona_id == Zona.id)
            .where(Router.is_enabled == True)
        )
        result = await session.exec(stmt)

        for router, zona_nombre in result:
            data = router.model_dump()
            data["zona_nombre"] = zona_nombre or f"Zona_{router.zona_id or 'General'}"
            
            # Decrypt password
            if data.get("password"):
                try:
                    data["password"] = decrypt_data(data["password"])
                except Exception:
                    pass
            
            routers.append(data)

    except Exception as e:
        logging.error(f"Error fetching routers for backup: {e}")

    return routers
