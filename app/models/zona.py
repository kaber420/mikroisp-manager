from typing import List, Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Relationship

# Modelo Principal
class Zona(SQLModel, table=True):
    __tablename__ = "zonas"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True)
    direccion: Optional[str] = None
    coordenadas_gps: Optional[str] = None
    notas_generales: Optional[str] = None
    notas_sensibles: Optional[str] = None
    
    # Relaciones
    infraestructura: Optional["ZonaInfra"] = Relationship(back_populates="zona", sa_relationship_kwargs={"uselist": False})
    documentos: List["ZonaDocumento"] = Relationship(back_populates="zona")
    notes: List["ZonaNote"] = Relationship(back_populates="zona")

# Modelos Satélite
class ZonaInfra(SQLModel, table=True):
    __tablename__ = "zona_infraestructura"
    id: Optional[int] = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id", unique=True)
    direccion_ip_gestion: Optional[str] = None
    gateway_predeterminado: Optional[str] = None
    servidores_dns: Optional[str] = None
    vlans_utilizadas: Optional[str] = None
    equipos_criticos: Optional[str] = None
    proximo_mantenimiento: Optional[date] = None
    
    zona: Optional[Zona] = Relationship(back_populates="infraestructura")

class ZonaDocumento(SQLModel, table=True):
    __tablename__ = "zona_documentos"
    id: Optional[int] = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id")
    tipo: str
    nombre_original: str
    nombre_guardado: str = Field(unique=True)
    descripcion: Optional[str] = None
    creado_en: datetime = Field(default_factory=datetime.utcnow)
    
    zona: Optional[Zona] = Relationship(back_populates="documentos")

class ZonaNote(SQLModel, table=True):
    __tablename__ = "zona_notes"
    id: Optional[int] = Field(default=None, primary_key=True)
    zona_id: int = Field(foreign_key="zonas.id")
    title: str
    content: Optional[str] = None
    is_encrypted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    zona: Optional[Zona] = Relationship(back_populates="notes")
