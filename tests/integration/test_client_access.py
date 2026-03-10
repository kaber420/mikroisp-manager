import pytest
import uuid
from httpx import AsyncClient

from app.models.user import User
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

@pytest.mark.asyncio
async def test_generate_client_access(client: AsyncClient, db_session: AsyncSession):
    # 0. Setup inicial: Inyectar admin directamente
    admin = User(
        username="admin_test",
        email="admin@test.com",
        hashed_password="hashed_password", # No importa el hash para el middleware de setup
        role="admin",
        is_active=True,
        is_superuser=True,
        is_verified=True
    )
    db_session.add(admin)
    await db_session.commit()
    
    # Login para obtener la cookie (necesitamos password correcto si el middleware de auth valida contra DB)
    # Sin embargo, para que /api/clients no redirija a /setup, basta con que exista el usuario en DB.
    # Para el test_generate_client_access, el login es necesario para el 401.
    
    # IMPORTANTE: El login fallará si hashed_password no es válido para passlib. 
    # Usaremos el approach de test_auth.py: crear vía /setup es más seguro para el hash.
    # Pero si /setup falla por redirección... probaremos inyectando y saltando auth para simplificar si es necesario.
    
    # Re-intento vía /setup pero asegurando persistencia
    setup_payload = {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "password123"
    }
    await client.post("/setup", json=setup_payload, headers={"Origin": "http://testserver"})
    
    # Login
    login_data = {"username": "admin_test", "password": "password123"}
    await client.post("/auth/cookie/login", data=login_data, headers={"Origin": "http://testserver"})

    # 1. Crear un cliente
    client_data = {
        "name": "Cliente de Prueba",
        "email": "testclient@example.com",
        "service_status": "active"
    }
    create_resp = await client.post(
        "/api/clients", 
        json=client_data,
        headers={"Origin": "http://testserver", "Referer": "http://testserver/"}
    )
    assert create_resp.status_code == 201
    client_id = create_resp.json()["id"]

    # 2. Generar acceso para ese cliente
    user_data = {
        "username": "testuser_client",
        "email": "testclient@example.com",
        "password": "secretpassword123",
        "role": "client",
        "telegram_chat_id": "987654321"
    }
    
    access_resp = await client.post(
        f"/api/clients/{client_id}/generate-access", 
        json=user_data,
        headers={"Origin": "http://testserver", "Referer": "http://testserver/"}
    )
    assert access_resp.status_code == 200
    
    created_user = access_resp.json()
    assert created_user["username"] == "testuser_client"
    assert created_user["client_id"] == client_id
    assert created_user["role"] == "client"
