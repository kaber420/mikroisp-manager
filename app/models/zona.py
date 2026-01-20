from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel


# Modelo Principal
class Zona(SQLModel, table=True):
    __tablename__ = "zonas"
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True)
    direccion: str | None = None
    coordenadas_gps: str | None = None
    notas_generales: str | None = None
    notas_sensibles: str | None = None
    rack_layout: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Relaciones
    infraestructura: Optional["ZonaInfra"] = Relationship(
        back_populates="zona", sa_relationship_kwargs={"uselist": False}
    )
    documentos: list["ZonaDocumento"] = Relationship(back_populates="zona")
    notes: list["ZonaNote"] = Relationship(back_populates="zona")


# Modelos Satélite
class ZonaInfra(SQLModel, table=True):
    __tablename__ = "zona_infraestructura"
    id: int | None = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id", unique=True)
    direccion_ip_gestion: str | None = None
    gateway_predeterminado: str | None = None
    servidores_dns: str | None = None
    vlans_utilizadas: str | None = None
    equipos_criticos: str | None = None
    proximo_mantenimiento: date | None = None

    zona: Zona | None = Relationship(back_populates="infraestructura")


class ZonaDocumento(SQLModel, table=True):
    __tablename__ = "zona_documentos"
    id: int | None = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id")
    tipo: str
    nombre_original: str
    nombre_guardado: str = Field(unique=True)
    descripcion: str | None = None
    creado_en: datetime = Field(default_factory=datetime.utcnow)

    zona: Zona | None = Relationship(back_populates="documentos")


class ZonaNote(SQLModel, table=True):
    __tablename__ = "zona_notes"
    id: int | None = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id")
    title: str
    content: str | None = None
    is_encrypted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    zona: Zona | None = Relationship(back_populates="notes")
