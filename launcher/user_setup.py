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

# Inicializador de tablas Legacy (Vital)
from app.db.init_db import setup_databases
from app.models.user import User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def check_and_create_first_user() -> None:
    """
    Verifica/Crea el usuario admin (Compatible con SQLModel).
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

    except Exception as e:
        logging.critical(f"Error inicializando BD: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
