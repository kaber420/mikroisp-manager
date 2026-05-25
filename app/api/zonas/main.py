# app/api/zonas/main.py

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import require_technician
from ...db.engine import get_session
from ...middleware.degraded_mode import verify_not_degraded
from ...models.user import User

from ...services.network.zone_service import ZoneService
from .models import (
    Zona,
    ZonaCreate,
    ZonaDetail,
    ZonaDocumento,
    ZonaInfra,
    ZonaNote,
    ZonaNoteCreate,
    ZonaNoteUpdate,
    ZonaUpdate,
)

router = APIRouter()


# --- Dependencia del Inyector de Servicio ---
async def get_zone_service(session: AsyncSession = Depends(get_session)) -> ZoneService:
    return ZoneService(session)


# --- API Endpoints ---
@router.post("/zonas", response_model=Zona, status_code=status.HTTP_201_CREATED)
async def create_zona(
    zona: ZonaCreate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    new_zona = await service.create_zona(zona.nombre)
    return new_zona


@router.get("/zonas", response_model=list[Zona])
async def get_all_zonas(
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    return await service.get_all_zonas()


@router.get("/zonas/{zona_id}", response_model=Zona)
async def get_zona(
    zona_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    return await service.get_zona(zona_id)


@router.put("/zonas/{zona_id}", response_model=Zona)
async def update_zona(
    zona_id: int,
    zona_update: ZonaUpdate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    updates = zona_update.model_dump(exclude_unset=True)
    updated_zona = await service.update_zona(zona_id, updates)
    return updated_zona


@router.delete("/zonas/{zona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zona(
    zona_id: int,
    request: Request,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    from ...core.audit import log_action

    await service.delete_zona(zona_id)
    log_action("DELETE", "zona", str(zona_id), user=current_user, request=request)
    return


# --- Endpoints de Detalles y Documentación ---
@router.get("/zonas/{zona_id}/details", response_model=ZonaDetail)
async def get_zona_details(
    zona_id: int,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
):
    return await service.get_zona_details(zona_id)


@router.put("/zonas/{zona_id}/infraestructura", response_model=ZonaInfra)
async def update_infraestructura(
    zona_id: int,
    infra_update: ZonaInfra,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    update_data = infra_update.model_dump(exclude={"id", "zona_id"}, exclude_unset=True)
    updated_infra = await service.update_infraestructura(zona_id, update_data)
    return updated_infra


@router.post(
    "/zonas/{zona_id}/documentos",
    response_model=ZonaDocumento,
    status_code=status.HTTP_201_CREATED,
)
async def upload_documento(
    zona_id: int,
    file: UploadFile = File(...),
    descripcion: str | None = Form(None),
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    new_doc = await service.upload_documento(zona_id, file, descripcion)
    return new_doc


# --- Endpoints de Notas ---
@router.post(
    "/zonas/{zona_id}/notes",
    response_model=ZonaNote,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    zona_id: int,
    note: ZonaNoteCreate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    new_note = await service.create_note_for_zona(
        zona_id, note.title, note.content, note.is_encrypted
    )
    return new_note


@router.put("/zonas/notes/{note_id}", response_model=ZonaNote)
async def update_note(
    note_id: int,
    note: ZonaNoteUpdate,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    updated_note = await service.update_note(note_id, note.title, note.content, note.is_encrypted)
    return updated_note


@router.delete("/zonas/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    request: Request,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    from ...core.audit import log_action

    await service.delete_note(note_id)
    log_action("DELETE", "zona_note", str(note_id), user=current_user, request=request)
    return


@router.delete("/documentos/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_documento(
    doc_id: int,
    request: Request,
    service: ZoneService = Depends(get_zone_service),
    current_user: User = Depends(require_technician),
    _: bool = Depends(verify_not_degraded),
):
    from ...core.audit import log_action

    await service.delete_documento(doc_id)
    log_action("DELETE", "documento", str(doc_id), user=current_user, request=request)
    return
