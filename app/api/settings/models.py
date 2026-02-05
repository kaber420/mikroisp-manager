from pydantic import BaseModel
from typing import Optional

class SettingUpdate(BaseModel):
    key: str
    value: str

class SystemSettingsRequest(BaseModel):
    # Database Config
    db_provider: str  # "sqlite" or "postgres"
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_host: Optional[str] = "localhost"
    postgres_port: Optional[str] = "5432"
    postgres_db: Optional[str] = "umanager"
    
    # Cache Config
    cache_provider: str  # "memory" or "redict"
    redict_url: Optional[str] = None 
