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
    client_id: Optional[str] = Field(default=None)  # UUID string vinculado a tabla clientes
