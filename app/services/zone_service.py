# app/services/zone_service.py
"""
ZoneService: Service layer for Zone CRUD operations.
Inherits from BaseCRUDService and adds zone-specific logic (encryption, dependency checks).
"""

import os
import uuid
from datetime import datetime
from typing import Any

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..models.zona import Zona, ZonaDocumento, ZonaInfra, ZonaNote
from ..utils.security import decrypt_data, encrypt_data
from .base_service import BaseCRUDService


class ZoneService(BaseCRUDService[Zona]):
    """
    Service for Zone CRUD operations.
    Inherits generic methods from BaseCRUDService and adds zone-specific logic:
    - Encryption/decryption of sensitive notes
    - Dependency checks before deletion (APs, Routers)
    - FileNotFoundError exceptions for backward compatibility with controllers
    """

    def __init__(self, session: Session):
        super().__init__(session, Zona)

    # --- Overridden CRUD methods for backward compatibility ---

    def create_zona(self, nombre: str) -> Zona:
        """Create a new zone with uniqueness validation."""
        existing = self.session.exec(select(Zona).where(Zona.nombre == nombre)).first()
        if existing:
            raise ValueError(f"El nombre de la zona '{nombre}' ya existe.")

        new_zona = Zona(nombre=nombre)
        self.session.add(new_zona)
        try:
            self.session.commit()
            self.session.refresh(new_zona)
            return new_zona
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"El nombre de la zona '{nombre}' ya existe.")

    def get_all_zonas(self) -> list[Zona]:
        """Get all zones ordered by name. Uses inherited get_all with custom ordering."""
        return self.session.exec(select(Zona).order_by(Zona.nombre)).all()

    def get_zona(self, zona_id: int) -> Zona:
        """
        Get zone by ID with decryption of sensitive notes.
        Raises FileNotFoundError for backward compatibility with controllers.
        """
        try:
            zona = super().get_by_id(zona_id)
        except HTTPException:
            # Re-raise as FileNotFoundError for backward compatibility
            raise FileNotFoundError("Zona no encontrada.")

        # Decrypt sensitive notes if present
        if zona.notas_sensibles:
            zona.notas_sensibles = decrypt_data(zona.notas_sensibles)
        return zona

    def update_zona(self, zona_id: int, update_data: dict[str, Any]) -> Zona:
        """
        Update zone with encryption of sensitive notes.
        Raises FileNotFoundError for backward compatibility.
        """
        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada.")

        if "notas_sensibles" in update_data and update_data["notas_sensibles"]:
            update_data["notas_sensibles"] = encrypt_data(update_data["notas_sensibles"])

        for key, value in update_data.items():
            setattr(zona, key, value)

        try:
            self.session.add(zona)
            self.session.commit()
            self.session.refresh(zona)
        except IntegrityError:
            self.session.rollback()
            raise ValueError("El nombre de la zona ya existe.")

        if zona.notas_sensibles:
            zona.notas_sensibles = decrypt_data(zona.notas_sensibles)
        return zona

    def delete_zona(self, zona_id: int):
        """
        Delete zone with dependency checks (APs, Routers).
        Raises FileNotFoundError for backward compatibility.
        """
        from ..models.ap import AP
        from ..models.router import Router

        # Check for APs in zone
        res_aps = self.session.exec(
            select(AP).where(AP.zona_id == zona_id).limit(1)
        ).first()
        if res_aps:
            raise ValueError("No se puede eliminar la zona porque contiene APs.")

        # Check for Routers in zone
        res_routers = self.session.exec(
            select(Router).where(Router.zona_id == zona_id).limit(1)
        ).first()
        if res_routers:
            raise ValueError("No se puede eliminar la zona porque contiene Routers.")

        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada para eliminar.")

        self.session.delete(zona)
        self.session.commit()

    # --- Zone Details and Documentation Methods ---

    def get_zona_details(self, zona_id: int) -> Zona:
        """Get zone with all details and decrypted notes."""
        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada.")

        if zona.notas_sensibles:
            zona.notas_sensibles = decrypt_data(zona.notas_sensibles)

        # Decrypt note content for encrypted notes
        for note in zona.notes:
            if note.is_encrypted and note.content:
                note.content = decrypt_data(note.content)

        return zona

    def update_infraestructura(self, zona_id: int, infra_data: dict[str, Any]) -> ZonaInfra:
        """Update or create infrastructure data for a zone."""
        infra = self.session.exec(select(ZonaInfra).where(ZonaInfra.zona_id == zona_id)).first()

        if infra:
            for key, value in infra_data.items():
                setattr(infra, key, value)
            self.session.add(infra)
        else:
            infra = ZonaInfra(zona_id=zona_id, **infra_data)
            self.session.add(infra)

        self.session.commit()
        self.session.refresh(infra)
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
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Extensiones permitidas: {allowed_list}",
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
            raise Exception(f"No se pudo guardar el archivo: {e}")

        new_doc = ZonaDocumento(
            zona_id=zona_id,
            tipo=file_type,
            nombre_original=file.filename,
            nombre_guardado=saved_filename,
            descripcion=descripcion,
        )
        self.session.add(new_doc)
        self.session.commit()
        self.session.refresh(new_doc)
        return new_doc

    def delete_documento(self, doc_id: int):
        """Delete a document and its file."""
        doc = self.session.get(ZonaDocumento, doc_id)
        if not doc:
            raise FileNotFoundError("Documento no encontrado.")

        file_path = os.path.join("data", "uploads", "zonas", str(doc.zona_id), doc.nombre_guardado)
        if os.path.exists(file_path):
            os.remove(file_path)

        self.session.delete(doc)
        self.session.commit()

    # --- Note Methods ---

    def create_note_for_zona(
        self, zona_id: int, title: str, content: str, is_encrypted: bool
    ) -> ZonaNote:
        """Create a note for a zone with optional encryption."""
        final_content = encrypt_data(content) if is_encrypted else content

        new_note = ZonaNote(
            zona_id=zona_id, title=title, content=final_content, is_encrypted=is_encrypted
        )
        self.session.add(new_note)
        self.session.commit()
        self.session.refresh(new_note)

        if new_note.is_encrypted and new_note.content:
            new_note.content = decrypt_data(new_note.content)

        return new_note

    def get_note(self, note_id: int) -> ZonaNote:
        """Get a note by ID with decryption."""
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada.")

        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    def update_note(self, note_id: int, title: str, content: str, is_encrypted: bool) -> ZonaNote:
        """Update a note with optional encryption."""
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada para actualizar.")

        final_content = encrypt_data(content) if is_encrypted else content

        note.title = title
        note.content = final_content
        note.is_encrypted = is_encrypted
        note.updated_at = datetime.utcnow()

        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)

        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    def delete_note(self, note_id: int):
        """Delete a note by ID."""
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada para eliminar.")

        self.session.delete(note)
        self.session.commit()
