import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Configurar variables de entorno antes de cargar la aplicación
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "testing"
os.environ["APP_ENV"] = "testing"
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"
os.environ["ALLOWED_ORIGINS"] = "http://localhost,http://127.0.0.1,http://testserver"

# Importar app después de configurar el entorno
from app.main import app
from app.db.engine import engine
from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import SQLModel

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    # Setup de tablas temporales
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Rollback al final de toda la sesión
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    # Inicializar sesión async
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def client():
    # Cliente estático de FastAPI usando ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
