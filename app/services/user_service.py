# app/services/user_service.py

from fastapi_users.password import PasswordHelper
from sqlmodel import Session, select

# Importamos los modelos y esquemas modernos
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def get_all_users(self) -> list[User]:
        # SQLModel genera el SELECT * FROM users automáticamente
        statement = select(User)
        return self.session.exec(statement).all()

    def create_user(self, user_create: UserCreate) -> User:
        # Validar si ya existe
        existing_user = self.session.exec(
            select(User).where(User.username == user_create.username)
        ).first()
        if existing_user:
            raise ValueError("El nombre de usuario ya existe.")

        hashed_password = PasswordHelper().hash(user_create.password)

        # Crear instancia del modelo manualmente
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            role=user_create.role,
            telegram_chat_id=user_create.telegram_chat_id,
            receive_alerts=user_create.receive_alerts,
            receive_device_down_alerts=user_create.receive_device_down_alerts,
            receive_announcements=user_create.receive_announcements,
        )

        # Guardar
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user

    def update_user(self, username: str, user_update: UserUpdate) -> User:
        # Buscar usuario
        db_user = self.session.exec(select(User).where(User.username == username)).first()

        if not db_user:
            raise FileNotFoundError("Usuario no encontrado.")

        # Aplicar cambios solo si se enviaron
        update_data = user_update.model_dump(exclude_unset=True)

        if "disabled" in update_data:
            is_disabled = update_data.pop("disabled")
            db_user.is_active = not is_disabled

        if "password" in update_data and update_data["password"]:
            hashed = PasswordHelper().hash(update_data.pop("password"))
            db_user.hashed_password = hashed

        for key, value in update_data.items():
            setattr(db_user, key, value)

        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user

    def delete_user(self, username: str):
        db_user = self.session.exec(select(User).where(User.username == username)).first()

        if not db_user:
            raise FileNotFoundError("Usuario no encontrado.")

        self.session.delete(db_user)
        self.session.commit()

    def get_user_by_username(self, username: str) -> User | None:
        return self.session.exec(select(User).where(User.username == username)).first()
