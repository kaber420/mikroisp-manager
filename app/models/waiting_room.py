from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class WaitingRoomConfig(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    is_active: bool = Field(default=True)
    
    # Textos
    welcome_message: str = Field(default="Bienvenido a Soporte. Un técnico le atenderá en breve.")
    ticker_text: Optional[str] = Field(default=None) # Texto deslizante
    
    # Multimedia
    media_type: str = Field(default="image") # 'image', 'video', 'youtube'
    media_url: Optional[str] = Field(default=None) # URL de la imagen, video .mp4 o ID de YouTube
    audio_url: Optional[str] = Field(default=None) # URL de música de fondo (.mp3)
    
    # Configuración de Tiempo
    max_wait_minutes: int = Field(default=6)
    timeout_message: str = Field(default="Lo sentimos, no hay técnicos disponibles en este momento. Por favor, intente más tarde.")
    
    # Programación (Scheduling)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
