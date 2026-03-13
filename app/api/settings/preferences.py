from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ...db.engine import get_session
from ...models.preference import UserPreference, UserPreferenceCreate, UserPreferenceUpdate
from ...models.user import User
from ...core.users import current_active_user

router = APIRouter()


@router.get("/", response_model=list[UserPreference])
async def get_my_preferences(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Obtener todas las preferencias del usuario actual.
    Incluidas las globales (user_id = None).
    """
    stmt = select(UserPreference).where(
        (UserPreference.user_id == user.id) | (UserPreference.user_id == None)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{key}", response_model=UserPreference)
async def get_preference_by_key(
    key: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Obtener una preferencia específica por su llave (key).
    """
    stmt = select(UserPreference).where(
        UserPreference.key == key,
        ((UserPreference.user_id == user.id) | (UserPreference.user_id == None))
    )
    result = await session.execute(stmt)
    pref = result.scalars().first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preferencia no encontrada")
    return pref


@router.patch("/{key}", response_model=UserPreference)
async def update_preference(
    key: str,
    update_data: UserPreferenceUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Actualizar el valor o estado (ej. dismissed) de una preferencia específica.
    """
    stmt = select(UserPreference).where(
        UserPreference.key == key,
        UserPreference.user_id == user.id
    )
    result = await session.execute(stmt)
    pref = result.scalars().first()

    if not pref:
        # Si no existe, podemos crearla al vuelo para este usuario
        if update_data.value is None:
            update_data.value = "{}"  # Default si solo se envía status
        pref = UserPreference(
            key=key,
            user_id=user.id,
            value=update_data.value,
            status=update_data.status or "pending"
        )
        session.add(pref)
    else:
        # Actualizar valores
        if update_data.value is not None:
            pref.value = update_data.value
        if update_data.status is not None:
            pref.status = update_data.status

    await session.commit()
    await session.refresh(pref)
    return pref
