import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.user import User

@pytest_asyncio.fixture(autouse=True)
async def clear_users(db_session: AsyncSession):
    """Limpia todos los usuarios antes y después de cada test."""
    users = await db_session.exec(select(User))
    for u in users.all():
        await db_session.delete(u)
    await db_session.commit()

@pytest.mark.asyncio
async def test_create_initial_admin(client: AsyncClient):
    """Prueba la creación del primer administrador vía /setup."""
    
    # 1. Enviar datos válidos al setup
    payload = {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "password123"
    }
    
    response = await client.post(
        "/setup", 
        json=payload,
        headers={"Origin": "http://testserver"}
    )
    
    # Verifica que fue exitoso
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Administrador creado exitosamente" in data["message"]

@pytest.mark.asyncio
async def test_setup_blocked_after_first_user(client: AsyncClient, db_session: AsyncSession):
    """Prueba que /setup se bloquea si ya existe un usuario."""
    
    # 1. Crear un usuario directamente en la BBDD
    user = User(
        email="test@test.com", 
        hashed_password="hashed_password", 
        role="admin", 
        username="admin", 
        is_active=True, 
        is_superuser=True, 
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2. Intentar registrar otro usuario en /setup
    payload = {
        "username": "hacker",
        "email": "hacker@test.com",
        "password": "password123"
    }
    response = await client.post(
        "/setup", 
        json=payload,
        headers={
            "Origin": "http://testserver",
            "Accept": "application/json"
        },
        follow_redirects=False
    )
    
    # Debe ser rechazado con 403 Forbidden
    assert response.status_code == 403
    assert "sistema ya" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Prueba que el login con credenciales correctas devuelve una cookie."""
    
    # Pre-condición: Necesitamos un usuario creado a través de FastAPI Users (para que el hasher sea correcto)
    payload = {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "password123"
    }
    await client.post("/setup", json=payload, headers={"Origin": "http://testserver"})
    
    # Usar el endpoint de FastAPI Users que recibe un form (username, password)
    data = {
        # Puesto que fastapi-users fue configurado para buscar por 'username' en la BD
        # (SQLAlchemyUserDatabaseByUsername), enviamos 'admin_test' no el email
        "username": "admin_test", 
        "password": "password123"
    }
    
    # Petición a la ruta de login de cookies
    response = await client.post(
        "/auth/cookie/login", 
        data=data,
        headers={"Origin": "http://testserver"}
    )
    
    # Verifica que el login fue exitoso (FastAPI users con auth_backend_cookie devuelve 200 o 204)
    assert response.status_code in (200, 204)
    
    # Verifica que se seteó la cookie de sesión
    assert "umonitorpro_access_token_v2" in response.cookies

@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient):
    """Prueba que el login con credenciales incorrectas falla."""
    
    # Pre-condición: Usuario válido
    payload = {"username": "admin_test", "email": "admin@test.com", "password": "password123"}
    await client.post("/setup", json=payload, headers={"Origin": "http://testserver"})
    
    data = {"username": "admin@test.com", "password": "wrongpassword"}
    
    response = await client.post(
        "/auth/cookie/login", 
        data=data,
        headers={"Origin": "http://testserver"}
    )
    
    # Verifica que el login fue rechazado (en este app, el handler custom da 429 por template)
    # Como Origin Shield usa RateLimiter que devuelve rate limit si es spam
    # Para credenciales invalidas fastapi-users devuelve 400
    assert response.status_code in (400, 429)
    assert "LOGIN_BAD_CREDENTIALS" in response.text



@pytest.mark.asyncio
async def test_api_protected_route_without_auth(client: AsyncClient):
    """Prueba que un endpoint de API rechaza el acceso sin cookie."""
    
    # Intentar acceder a la API de clientes
    response = await client.get("/api/clients")
    
    # Como es /api/, devuelve JSON con 401 Unauthorized
    assert response.status_code == 401
    assert "Unauthorized" in response.text
