# app/db/zonas_db.py
"""
CRUD operations for Zonas and related tables using SQLModel and AsyncSession.
"""

import logging
import os
from typing import Any, Sequence

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from ..models.zona import Zona, ZonaDocumento, ZonaInfra, ZonaNote
from ..models.ap import AP
from ..models.router import Router
from ..utils.security import decrypt_data, encrypt_data

logger = logging.getLogger(__name__)


# --- Funciones de Zonas (CRUD Básico) ---


async def create_zona(session: AsyncSession, nombre: str) -> Zona:
    zona = Zona(nombre=nombre)
    session.add(zona)
    try:
        await session.commit()
        await session.refresh(zona)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"El nombre de la zona '{nombre}' ya existe. Error: {e}")
    return zona


async def get_all_zonas(session: AsyncSession) -> Sequence[Zona]:
    stmt = select(Zona).order_by(Zona.nombre)
    result = await session.exec(stmt)
    return result.all()


async def update_zona_details(
    session: AsyncSession, zona_id: int, updates: dict[str, Any]
) -> Zona | None:
    if not updates:
        return await get_zona_by_id(session, zona_id)

    try:
        zona = await session.get(Zona, zona_id)
        if not zona:
            return None

        # Encrypt sensitive notes if present
        if "notas_sensibles" in updates and updates["notas_sensibles"] is not None:
            updates["notas_sensibles"] = encrypt_data(updates["notas_sensibles"])

        for key, value in updates.items():
            if hasattr(zona, key):
                setattr(zona, key, value)

        session.add(zona)
        await session.commit()
        await session.refresh(zona)
        return zona
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Error actualizando zona: {e}")


async def delete_zona(session: AsyncSession, zona_id: int) -> int:
    # Check for APs in zone
    stmt_aps = select(AP).where(AP.zona_id == zona_id).limit(1)
    result_aps = await session.exec(stmt_aps)
    if result_aps.first():
        raise ValueError("No se puede eliminar la zona porque contiene APs.")

    # Check for Routers in zone
    stmt_routers = select(Router).where(Router.zona_id == zona_id).limit(1)
    result_routers = await session.exec(stmt_routers)
    if result_routers.first():
        raise ValueError("No se puede eliminar la zona porque contiene Routers.")

    zona = await session.get(Zona, zona_id)
    if not zona:
        return 0

    await session.delete(zona)
    await session.commit()
    return 1


async def get_zona_by_id(session: AsyncSession, zona_id: int) -> Zona | None:
    zona = await session.get(Zona, zona_id)
    if not zona:
        return None

    # Decrypt sensitive notes
    zona_out = zona.model_copy()
    if zona_out.notas_sensibles:
        try:
            zona_out.notas_sensibles = decrypt_data(zona_out.notas_sensibles)
        except Exception as e:
            logger.error(f"Error decrypting notas_sensibles for zona {zona_id}: {e}")
    return zona_out


# --- Funciones de Infraestructura ---


async def get_infra_by_zona_id(session: AsyncSession, zona_id: int) -> ZonaInfra | None:
    stmt = select(ZonaInfra).where(ZonaInfra.zona_id == zona_id)
    result = await session.exec(stmt)
    return result.first()


async def update_or_create_infra(
    session: AsyncSession, zona_id: int, infra_data: dict[str, Any]
) -> ZonaInfra | None:
    if not infra_data:
        return await get_infra_by_zona_id(session, zona_id)

    try:
        existing_infra = await get_infra_by_zona_id(session, zona_id)

        if existing_infra:
            for key, value in infra_data.items():
                if hasattr(existing_infra, key):
                    setattr(existing_infra, key, value)
            session.add(existing_infra)
        else:
            new_infra = ZonaInfra(zona_id=zona_id, **infra_data)
            session.add(new_infra)

        await session.commit()
        return await get_infra_by_zona_id(session, zona_id)
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating/creating infra for zona {zona_id}: {e}")
        return None


# --- Funciones de Documentos ---


async def get_docs_by_zona_id(session: AsyncSession, zona_id: int) -> Sequence[ZonaDocumento]:
    stmt = (
        select(ZonaDocumento)
        .where(ZonaDocumento.zona_id == zona_id)
        .order_by(ZonaDocumento.creado_en.desc())
    )
    result = await session.exec(stmt)
    return result.all()


async def add_document(session: AsyncSession, doc_data: dict[str, Any]) -> ZonaDocumento:
    doc = ZonaDocumento(**doc_data)
    session.add(doc)
    try:
        await session.commit()
        await session.refresh(doc)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Error adding document: {e}")
    return doc


async def get_document_by_id(session: AsyncSession, doc_id: int) -> ZonaDocumento | None:
    return await session.get(ZonaDocumento, doc_id)


async def delete_document(session: AsyncSession, doc_id: int) -> int:
    doc = await session.get(ZonaDocumento, doc_id)
    if not doc:
        return 0

    # Delete physical file
    file_path = os.path.join("uploads", "zonas", str(doc.zona_id), doc.nombre_guardado)
    if os.path.exists(file_path):
        os.remove(file_path)

    await session.delete(doc)
    await session.commit()
    return 1


# --- Funciones de Notas ---


async def create_note(
    session: AsyncSession, zona_id: int, title: str, content: str, is_encrypted: bool
) -> ZonaNote:
    final_content = encrypt_data(content) if is_encrypted else content

    note = ZonaNote(
        zona_id=zona_id, title=title, content=final_content, is_encrypted=is_encrypted
    )
    session.add(note)
    try:
        await session.commit()
        await session.refresh(note)
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Error creating note: {e}")

    return await get_note_by_id(session, note.id)


async def get_note_by_id(session: AsyncSession, note_id: int) -> ZonaNote | None:
    note = await session.get(ZonaNote, note_id)
    if not note:
        return None

    note_out = note.model_copy()
    if note_out.is_encrypted and note_out.content:
        try:
            note_out.content = decrypt_data(note_out.content)
        except Exception as e:
            logger.error(f"Error decrypting note {note_id}: {e}")
    return note_out


async def get_notes_by_zona_id(session: AsyncSession, zona_id: int) -> list[ZonaNote]:
    stmt = (
        select(ZonaNote)
        .where(ZonaNote.zona_id == zona_id)
        .order_by(ZonaNote.updated_at.desc())
    )
    result = await session.exec(stmt)
    notes = result.all()

    output = []
    for note in notes:
        note_out = note.model_copy()
        if note_out.is_encrypted and note_out.content:
            try:
                note_out.content = decrypt_data(note_out.content)
            except Exception:
                pass
        output.append(note_out)
    return output


async def update_note(
    session: AsyncSession, note_id: int, title: str, content: str, is_encrypted: bool
) -> ZonaNote | None:
    note = await session.get(ZonaNote, note_id)
    if not note:
        return None

    note.title = title
    note.content = encrypt_data(content) if is_encrypted else content
    note.is_encrypted = is_encrypted

    session.add(note)
    await session.commit()
    await session.refresh(note)

    return await get_note_by_id(session, note_id)


async def delete_note(session: AsyncSession, note_id: int) -> int:
    note = await session.get(ZonaNote, note_id)
    if not note:
        return 0

    await session.delete(note)
    await session.commit()
    return 1
