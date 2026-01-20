# app/api/zonas/models.py
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# --- Modelos Pydantic (Movidos) ---
class Zona(BaseModel):
    id: int
    nombre: str
    rack_layout: dict[str, Any] | None = None
    model_config = ConfigDict(from_attributes=True)


class ZonaCreate(BaseModel):
    nombre: str


class ZonaUpdate(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    coordenadas_gps: str | None = None
    rack_layout: dict[str, Any] | None = None


class ZonaInfra(BaseModel):
    id: int | None = None
    zona_id: int
    direccion_ip_gestion: str | None = None
    gateway_predeterminado: str | None = None
    servidores_dns: str | None = None
    vlans_utilizadas: str | None = None
    equipos_criticos: str | None = None
    proximo_mantenimiento: date | None = None
    model_config = ConfigDict(from_attributes=True)


class ZonaDocumento(BaseModel):
    id: int

    zona_id: int

    tipo: str

    nombre_original: str

    nombre_guardado: str

    descripcion: str | None = None

    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Modelos de Notas ---


class ZonaNoteBase(BaseModel):
    title: str

    content: str | None = None

    is_encrypted: bool = False


class ZonaNoteCreate(ZonaNoteBase):
    pass


class ZonaNoteUpdate(ZonaNoteBase):
    pass


class ZonaNote(ZonaNoteBase):
    id: int

    zona_id: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZonaDetail(Zona):
    direccion: str | None = None
    coordenadas_gps: str | None = None
    infraestructura: ZonaInfra | None = None
    documentos: list[ZonaDocumento] = []
    notes: list[ZonaNote] = []
    # rack_layout is inherited from Zona
