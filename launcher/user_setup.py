# launcher/user_setup.py
"""Creación del usuario administrador inicial."""

import getpass
import logging
import sys
import uuid

from passlib.context import CryptContext
from sqlmodel import Session, select

# Motor Síncrono
from app.db.engine_sync import create_sync_db_and_tables, sync_engine

from app.db.init_db import setup_databases
from app.models.user import User

from sqlalchemy import create_engine
import os
from app.models.setting import Setting
from app.models.zona import Zona
from app.models.router import Router
from app.models.plan import Plan
from app.models.client import Client

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def _attempt_auto_migrate(target_session: Session) -> bool:
    """Investiga si hay datos en una base local SQLite y los copia al nuevo motor en el orden correcto."""
    try:
        from app.core.config import settings
        if "postgres" not in settings.DATABASE_URL_SYNC:
            return False
            
        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
        
        if not os.path.exists(DATABASE_FILE):
            return False
            
        sqlite_engine = create_engine(f"sqlite:///{DATABASE_FILE}")
        with Session(sqlite_engine) as sqlite_session:
            # 1. Configuración (Independiente)
            settings_to_migrate = sqlite_session.exec(select(Setting)).all()
            if settings_to_migrate:
                logging.info(f"🔄 Migrando {len(settings_to_migrate)} configuraciones...")
                for s in settings_to_migrate:
                    exists = target_session.exec(select(Setting).where(Setting.key == s.key)).first()
                    if not exists:
                        target_session.add(Setting(**s.model_dump()))
                target_session.flush()

            # 2. Zonas (Independiente)
            zonas = sqlite_session.exec(select(Zona)).all()
            if zonas:
                logging.info(f"🔄 Migrando {len(zonas)} zonas...")
                for z in zonas:
                    exists = target_session.exec(select(Zona).where(Zona.id == z.id)).first()
                    if not exists:
                        target_session.add(Zona(**z.model_dump()))
                target_session.flush()

            # 3. Routers (Depende de Zonas)
            routers = sqlite_session.exec(select(Router)).all()
            if routers:
                logging.info(f"🔄 Migrando {len(routers)} routers...")
                for r in routers:
                    exists = target_session.exec(select(Router).where(Router.host == r.host)).first()
                    if not exists:
                        target_session.add(Router(**r.model_dump()))
                target_session.flush()

            # 4. Planes (Depende de Routers)
            planes = sqlite_session.exec(select(Plan)).all()
            if planes:
                logging.info(f"🔄 Migrando {len(planes)} planes...")
                for p in planes:
                    exists = target_session.exec(select(Plan).where(Plan.id == p.id)).first()
                    if not exists:
                        target_session.add(Plan(**p.model_dump()))
                target_session.flush()

            # 5. Clientes (Depende de Planes/Zonas opcionalmente)
            clients = sqlite_session.exec(select(Client)).all()
            if clients:
                logging.info(f"🔄 Migrando {len(clients)} clientes...")
                for c in clients:
                    exists = target_session.exec(select(Client).where(Client.id == c.id)).first()
                    if not exists:
                        target_session.add(Client(**c.model_dump()))
                target_session.flush()

            # 6. Usuarios (Depende de Clientes)
            users_to_migrate = sqlite_session.exec(select(User)).all()
            if users_to_migrate:
                logging.info(f"🔄 Migrando {len(users_to_migrate)} usuarios...")
                for u in users_to_migrate:
                    exists = target_session.exec(select(User).where(User.id == u.id)).first()
                    if not exists:
                        target_session.add(User(**u.model_dump()))

            target_session.commit()
            logging.info("✅ Migración completa de datos exitosa.")
            return True
            
    except Exception as e:
        logging.error(f"❌ Error durante la auto-migración de datos: {e}")
        target_session.rollback()
        return False


def check_and_create_first_user(interactive: bool = False) -> None:
    """
    Verifica/Crea el usuario admin (Compatible con SQLModel).
    
    Args:
        interactive: If True, prompts for user input in CLI. 
                     If False (default), logs a message and returns without blocking.
    """
    try:
        # 1. Crear tablas modernas
        create_sync_db_and_tables()
        # 2. Crear tablas legacy (Settings, etc.)
        setup_databases()

        with Session(sync_engine) as session:
            if session.exec(select(User)).first():
                logging.info("Sistema validado (Usuarios existentes).")
                return

            if _attempt_auto_migrate(session):
                return

            # No user exists - handle based on mode
            if interactive:
                # Interactive mode: CLI prompts
                print("=" * 60)
                print("🔐 CREACIÓN DEL ADMINISTRADOR")
                print("=" * 60)

                username = input("👤 Usuario: ").strip()
                while not username:
                    username = input("👤 Usuario: ").strip()

                email = input("📧 Email: ").strip()
                while not email:
                    email = input("📧 Email: ").strip()

                while True:
                    password = getpass.getpass("🔑 Contraseña: ")
                    if len(password) >= 6:
                        if getpass.getpass("🔑 Confirmar: ") == password:
                            break
                        print("❌ No coinciden.")
                    else:
                        print("❌ Mínimo 6 caracteres.")

                hashed_password = pwd_context.hash(password)

                new_user = User(
                    id=uuid.uuid4(),
                    email=email,
                    username=username,
                    hashed_password=hashed_password,
                    role="admin",
                    is_active=True,
                    is_superuser=True,
                    is_verified=True,
                )
                session.add(new_user)
                session.commit()
                print(f"\n✅ Administrador '{username}' creado exitosamente.\n")
            else:
                # Non-interactive mode: Don't block, inform user
                print("=" * 60)
                print("⚠️  NO HAY USUARIOS EN EL SISTEMA")
                print("=" * 60)
                print("   Opciones para crear el primer administrador:")
                print("   1. Web Setup:  Visita http://localhost:7777/setup")
                print("   2. CLI Setup:  python launcher.py setup")
                print("   3. Env Vars:   ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME")
                print("=" * 60)
                logging.warning("No users found. Waiting for setup via web or CLI.")

    except Exception as e:
        logging.critical(f"Error inicializando BD: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

