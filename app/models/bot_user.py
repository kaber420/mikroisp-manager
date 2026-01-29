from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class BotUser(SQLModel, table=True):
    __tablename__ = "bot_users"
    
    telegram_id: str = Field(primary_key=True, index=True)
    first_name: Optional[str] = None
    username: Optional[str] = None
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    is_client: bool = Field(default=False)
    client_id: Optional[int] = Field(default=None) # Vinculado a tabla clientes si existe
