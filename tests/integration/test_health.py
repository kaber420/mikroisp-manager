import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_app_login_page_redirects_to_setup_when_empty(client: AsyncClient):
    """Prueba que el login redirige al asistente de configuración si no hay usuarios."""
    response = await client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/setup"

@pytest.mark.asyncio
async def test_setup_page_renders(client: AsyncClient):
    """Prueba que el setup renderiza."""
    response = await client.get("/setup", follow_redirects=True)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_db_session_injection(db_session):
    """Verifica que podemos invocar una sesión desde conftest sin errores."""
    assert db_session is not None
