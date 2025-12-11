# app/api/zonas/main.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import List, Optional

from ...core.users import require_technician
from ...models.user import User
from ...services.zone_service import ZoneService
from ...db.engine_sync import get_sync_session
from sqlmodel import Session
from .models import (
    Zona,
    ZonaCreate,
    ZonaUpdate,
    ZonaInfra,
    ZonaDocumento,
    ZonaDetail,
    ZonaNote,
    ZonaNoteCreate,
    ZonaNoteUpdate,
)

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
def get_zone_service(session: Session = Depends(get_sync_session)) -> ZoneService:
    return ZoneService(session)


# --- API Endpoints ---
@router.post("/zonas", response_model=Zona, status_code=status.HTTP_201_CREATED)
def create_zona(
    zona: ZonaCreate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        new_zona = service.create_zona(zona.nombre)
        return new_zona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/zonas", response_model=List[Zona])
def get_all_zonas(
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    return service.get_all_zonas()


@router.get("/zonas/{zona_id}", response_model=Zona)
def get_zona(
    zona_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        zona = service.get_zona(zona_id)
        return zona
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/zonas/{zona_id}", response_model=Zona)
def update_zona(
    zona_id: int,
    zona_update: ZonaUpdate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    updates = zona_update.model_dump(exclude_unset=True)
    try:
        updated_zona = service.update_zona(zona_id, updates)
        return updated_zona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/zonas/{zona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zona(
    zona_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        service.delete_zona(zona_id)
        return
    except ValueError as e:  # Constraint error
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Endpoints de Detalles y Documentación ---
@router.get("/zonas/{zona_id}/details", response_model=ZonaDetail)
def get_zona_details(
    zona_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        return service.get_zona_details(zona_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/zonas/{zona_id}/infraestructura", response_model=ZonaInfra)
def update_infraestructura(
    zona_id: int,
    infra_update: ZonaInfra,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    update_data = infra_update.model_dump(exclude={"id", "zona_id"}, exclude_unset=True)
    updated_infra = service.update_infraestructura(zona_id, update_data)
    return updated_infra


@router.post(
    "/zonas/{zona_id}/documentos",
    response_model=ZonaDocumento,
    status_code=status.HTTP_201_CREATED,
)
async def upload_documento(
    zona_id: int,
    file: UploadFile = File(...),
    descripcion: Optional[str] = Form(None),
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        new_doc = await service.upload_documento(zona_id, file, descripcion)
        return new_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Notas ---
@router.post(
    "/zonas/{zona_id}/notes",
    response_model=ZonaNote,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    zona_id: int,
    note: ZonaNoteCreate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        new_note = service.create_note_for_zona(
            zona_id, note.title, note.content, note.is_encrypted
        )
        return new_note
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/zonas/notes/{note_id}", response_model=ZonaNote)
def update_note(
    note_id: int,
    note: ZonaNoteUpdate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        updated_note = service.update_note(
            note_id, note.title, note.content, note.is_encrypted
        )
        return updated_note
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zonas/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        service.delete_note(note_id)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documentos/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_documento(
    doc_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    try:
        service.delete_documento(doc_id)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
