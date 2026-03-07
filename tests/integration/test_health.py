import pytest
from httpx import AsyncClient



@pytest.mark.asyncio
async def test_db_session_injection(db_session):
    """Verifica que podemos invocar una sesión desde conftest sin errores."""
    assert db_session is not None
