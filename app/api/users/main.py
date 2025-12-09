# app/api/users/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlmodel import Session

from ...auth import User as AuthUser, get_current_active_user
from ...db.engine_sync import get_sync_session
from ...services.user_service import UserService
from ...schemas.user import UserRead, UserCreate, UserUpdate

router = APIRouter()


# --- Inyección de Dependencias Actualizada ---
# Ahora inyectamos la sesión de SQLModel
def get_user_service(session: Session = Depends(get_sync_session)) -> UserService:
    return UserService(session)


@router.get("/users", response_model=List[UserRead])
def api_get_all_users(
    service: UserService = Depends(get_user_service),
    current_user: AuthUser = Depends(get_current_active_user),
):
    return service.get_all_users()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def api_create_user(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service),
    current_user: AuthUser = Depends(get_current_active_user),
):
    try:
        return service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{username}", response_model=UserRead)
def api_update_user(
    username: str,
    user_data: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: AuthUser = Depends(get_current_active_user),
):
    try:
        return service.update_user(username, user_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_user(
    username: str,
    service: UserService = Depends(get_user_service),
    current_user: AuthUser = Depends(get_current_active_user),
):
    if username == current_user.username:
        raise HTTPException(
            status_code=403, detail="No puedes eliminar tu propia cuenta."
        )
    try:
        service.delete_user(username)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
