# app/services/zone_service.py
"""
ZoneService: Service layer for Zone CRUD operations.
Inherits from AsyncBaseCRUDService and adds zone-specific logic (encryption, dependency checks).
"""

import os
import uuid
from datetime import datetime
from typing import Any

import aiofiles
from fastapi import UploadFile

from ...core.exceptions import (
    DeletionBlockedError,
    DuplicateError,
    NotFoundError,
    ValidationError,
    ZoneNotFoundError,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...models.zona import Zona, ZonaDocumento, ZonaInfra, ZonaNote
from ...utils.security import decrypt_data, encrypt_data
from ..core.base_service import AsyncBaseCRUDService


class ZoneService(AsyncBaseCRUDService[Zona]):
    """
    Service for Zone CRUD operations.
    Inherits generic methods from AsyncBaseCRUDService and adds zone-specific logic:
    - Encryption/decryption of sensitive notes
    - Dependency checks before deletion (APs, Routers)
    - FileNotFoundError exceptions for backward compatibility with controllers
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Zona)

    # --- Overridden CRUD methods for backward compatibility ---

    async def create_zona(self, nombre: str) -> Zona:
        """Create a new zone with uniqueness validation."""
        existing_result = await self.session.exec(select(Zona).where(Zona.nombre == nombre))
        existing = existing_result.first()
        if existing:
            raise DuplicateError(f"El nombre de la zona '{nombre}' ya existe.")

        new_zona = Zona(nombre=nombre)
        self.session.add(new_zona)
        try:
            await self.session.commit()
            await self.session.refresh(new_zona)
            return new_zona
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateError(f"El nombre de la zona '{nombre}' ya existe.")

    async def get_all_zonas(self) -> list[Zona]:
        """Get all zones ordered by name. Uses inherited get_all with custom ordering."""
        result = await self.session.exec(select(Zona).order_by(Zona.nombre))
        return result.all()

    async def get_zona(self, zona_id: int) -> Zona:
        """
        Get zone by ID.
        Raises FileNotFoundError for backward compatibility with controllers.
        """
        zona = await super().get_by_id(zona_id)
        return zona

    async def update_zona(self, zona_id: int, update_data: dict[str, Any]) -> Zona:
        """
        Update zone details.
        Raises FileNotFoundError for backward compatibility.
        """
        zona = await self.session.get(Zona, zona_id)
        if not zona:
            raise ZoneNotFoundError("Zona no encontrada.")

        for key, value in update_data.items():
            setattr(zona, key, value)

        try:
            self.session.add(zona)
            await self.session.commit()
            await self.session.refresh(zona)
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateError("El nombre de la zona ya existe.")
        return zona

    async def delete_zona(self, zona_id: int):
        """
        Delete zone with dependency checks (APs, Routers).
        Raises FileNotFoundError for backward compatibility.
        """
        from ...models.ap import AP
        from ...models.router import Router

        # Check for APs in zone
        res_aps_result = await self.session.exec(
            select(AP).where(AP.zona_id == zona_id).limit(1)
        )
        res_aps = res_aps_result.first()
        if res_aps:
            raise DeletionBlockedError("No se puede eliminar la zona porque contiene APs.")

        # Check for Routers in zone
        res_routers_result = await self.session.exec(
            select(Router).where(Router.zona_id == zona_id).limit(1)
        )
        res_routers = res_routers_result.first()
        if res_routers:
            raise DeletionBlockedError("No se puede eliminar la zona porque contiene Routers.")

        zona = await self.session.get(Zona, zona_id)
        if not zona:
            raise ZoneNotFoundError("Zona no encontrada para eliminar.")

        await self.session.delete(zona)
        await self.session.commit()

    # --- Zone Details and Documentation Methods ---

    async def get_zona_details(self, zona_id: int) -> Zona:
        """Get zone with all details and decrypted notes."""
        statement = select(Zona).where(Zona.id == zona_id).options(
            selectinload(Zona.notes),
            selectinload(Zona.documentos),
            selectinload(Zona.infraestructura)
        )
        result = await self.session.exec(statement)
        zona = result.first()
        if not zona:
            raise ZoneNotFoundError("Zona no encontrada.")

        # Decrypt note content for encrypted notes
        for note in zona.notes:
            if note.is_encrypted and note.content:
                note.content = decrypt_data(note.content)

        return zona

    async def update_infraestructura(self, zona_id: int, infra_data: dict[str, Any]) -> ZonaInfra:
        """Update or create infrastructure data for a zone."""
        infra_result = await self.session.exec(select(ZonaInfra).where(ZonaInfra.zona_id == zona_id))
        infra = infra_result.first()

        if infra:
            for key, value in infra_data.items():
                setattr(infra, key, value)
            self.session.add(infra)
        else:
            infra = ZonaInfra(zona_id=zona_id, **infra_data)
            self.session.add(infra)

        await self.session.commit()
        await self.session.refresh(infra)
        return infra

    # Allowed file extensions whitelist
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml"}
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_TEXT_EXTENSIONS

    async def upload_documento(
        self, zona_id: int, file: UploadFile, descripcion: str | None
    ) -> ZonaDocumento:
        """Upload a document for a zone. Only allows image and text files."""
        file_extension = os.path.splitext(file.filename)[1].lower()

        # Security: Validate file extension against whitelist
        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(self.ALLOWED_EXTENSIONS))
            raise ValidationError(
                f"Tipo de archivo no permitido. Extensiones permitidas: {allowed_list}"
            )

        file_type = "image" if file_extension in self.ALLOWED_IMAGE_EXTENSIONS else "document"
        saved_filename = f"{uuid.uuid4()}{file_extension}"

        save_dir = os.path.join("data", "uploads", "zonas", str(zona_id))
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, saved_filename)

        try:
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)
        except Exception as e:
            raise ValidationError(f"No se pudo guardar el archivo: {e}")

        new_doc = ZonaDocumento(
            zona_id=zona_id,
            tipo=file_type,
            nombre_original=file.filename,
            nombre_guardado=saved_filename,
            descripcion=descripcion,
        )
        self.session.add(new_doc)
        await self.session.commit()
        await self.session.refresh(new_doc)
        return new_doc

    async def delete_documento(self, doc_id: int):
        """Delete a document and its file."""
        doc = await self.session.get(ZonaDocumento, doc_id)
        if not doc:
            raise NotFoundError("Documento no encontrado.")

        file_path = os.path.join("data", "uploads", "zonas", str(doc.zona_id), doc.nombre_guardado)
        if os.path.exists(file_path):
            os.remove(file_path)

        await self.session.delete(doc)
        await self.session.commit()

    # --- Note Methods ---

    async def create_note_for_zona(
        self, zona_id: int, title: str, content: str, is_encrypted: bool
    ) -> ZonaNote:
        """Create a note for a zone with optional encryption."""
        final_content = encrypt_data(content) if is_encrypted else content

        new_note = ZonaNote(
            zona_id=zona_id, title=title, content=final_content, is_encrypted=is_encrypted
        )
        self.session.add(new_note)
        await self.session.commit()
        await self.session.refresh(new_note)

        if new_note.is_encrypted and new_note.content:
            new_note.content = decrypt_data(new_note.content)

        return new_note

    async def get_note(self, note_id: int) -> ZonaNote:
        """Get a note by ID with decryption."""
        note = await self.session.get(ZonaNote, note_id)
        if not note:
            raise NotFoundError("Nota no encontrada.")

        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    async def update_note(self, note_id: int, title: str, content: str, is_encrypted: bool) -> ZonaNote:
        """Update a note with optional encryption."""
        note = await self.session.get(ZonaNote, note_id)
        if not note:
            raise NotFoundError("Nota no encontrada para actualizar.")

        final_content = encrypt_data(content) if is_encrypted else content

        note.title = title
        note.content = final_content
        note.is_encrypted = is_encrypted
        note.updated_at = datetime.utcnow()

        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)

        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    async def delete_note(self, note_id: int):
        """Delete a note by ID."""
        note = await self.session.get(ZonaNote, note_id)
        if not note:
            raise NotFoundError("Nota no encontrada para eliminar.")

        await self.session.delete(note)
        await self.session.commit()
