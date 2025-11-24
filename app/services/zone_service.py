# app/services/zone_service.py
import os
import uuid
import aiofiles
from fastapi import UploadFile
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select, text
from sqlalchemy.exc import IntegrityError

from ..models.zona import Zona, ZonaInfra, ZonaDocumento, ZonaNote
from ..utils.security import encrypt_data, decrypt_data

class ZoneService:
    def __init__(self, session: Session):
        self.session = session

    def create_zona(self, nombre: str) -> Zona:
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

    def get_all_zonas(self) -> List[Zona]:
        return self.session.exec(select(Zona).order_by(Zona.nombre)).all()

    def get_zona(self, zona_id: int) -> Zona:
        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada.")
        
        # Decrypt sensitive notes if present
        if zona.notas_sensibles:
            zona.notas_sensibles = decrypt_data(zona.notas_sensibles)
        return zona

    def update_zona(self, zona_id: int, update_data: Dict[str, Any]) -> Zona:
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
        # Check for dependencies manually since they are not yet SQLModels
        # Check APs
        res_aps = self.session.exec(text("SELECT 1 FROM aps WHERE zona_id = :id"), params={"id": zona_id}).first()
        if res_aps:
            raise ValueError("No se puede eliminar la zona porque contiene APs.")
            
        # Check Routers
        res_routers = self.session.exec(text("SELECT 1 FROM routers WHERE zona_id = :id"), params={"id": zona_id}).first()
        if res_routers:
            raise ValueError("No se puede eliminar la zona porque contiene Routers.")

        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada para eliminar.")
            
        self.session.delete(zona)
        self.session.commit()

    # --- Métodos de Detalles y Documentación ---

    def get_zona_details(self, zona_id: int) -> Zona:
        # We return the Zona object, which has relationships loaded (or lazy loaded)
        # The Pydantic response model will handle serialization
        zona = self.session.get(Zona, zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada.")
        
        if zona.notas_sensibles:
            zona.notas_sensibles = decrypt_data(zona.notas_sensibles)
            
        return zona

    def update_infraestructura(
        self, zona_id: int, infra_data: Dict[str, Any]
    ) -> ZonaInfra:
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

    async def upload_documento(
        self, zona_id: int, file: UploadFile, descripcion: Optional[str]
    ) -> ZonaDocumento:
        file_type = "image" if file.content_type.startswith("image/") else "document"
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{uuid.uuid4()}{file_extension}"
        
        save_dir = os.path.join("uploads", "zonas", str(zona_id))
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
            descripcion=descripcion
        )
        self.session.add(new_doc)
        self.session.commit()
        self.session.refresh(new_doc)
        return new_doc

    def delete_documento(self, doc_id: int):
        doc = self.session.get(ZonaDocumento, doc_id)
        if not doc:
            raise FileNotFoundError("Documento no encontrado.")
            
        file_path = os.path.join(
            "uploads", "zonas", str(doc.zona_id), doc.nombre_guardado
        )
        if os.path.exists(file_path):
            os.remove(file_path)
            
        self.session.delete(doc)
        self.session.commit()

    # --- Métodos de Notas ---

    def create_note_for_zona(
        self, zona_id: int, title: str, content: str, is_encrypted: bool
    ) -> ZonaNote:
        final_content = encrypt_data(content) if is_encrypted else content
        
        new_note = ZonaNote(
            zona_id=zona_id,
            title=title,
            content=final_content,
            is_encrypted=is_encrypted
        )
        self.session.add(new_note)
        self.session.commit()
        self.session.refresh(new_note)
        
        if new_note.is_encrypted and new_note.content:
            new_note.content = decrypt_data(new_note.content)
            
        return new_note

    def get_note(self, note_id: int) -> ZonaNote:
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada.")
            
        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    def update_note(
        self, note_id: int, title: str, content: str, is_encrypted: bool
    ) -> ZonaNote:
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada para actualizar.")
            
        final_content = encrypt_data(content) if is_encrypted else content
        
        note.title = title
        note.content = final_content
        note.is_encrypted = is_encrypted
        note.updated_at = datetime.utcnow() # Manually update timestamp if not auto-updated by DB trigger (SQLModel default_factory only works on insert usually, unless sa_column_kwargs onupdate is set)
        
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        
        if note.is_encrypted and note.content:
            note.content = decrypt_data(note.content)
        return note

    def delete_note(self, note_id: int):
        note = self.session.get(ZonaNote, note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada para eliminar.")
            
        self.session.delete(note)
        self.session.commit()
