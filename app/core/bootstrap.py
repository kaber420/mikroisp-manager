# app/core/bootstrap.py
import logging
import uuid
from app.core.config import settings

from passlib.context import CryptContext
from sqlmodel import Session, select

# Re-use existing DB logic
from app.db.engine_sync import create_sync_db_and_tables, sync_engine, DATABASE_URL_SYNC
from app.db.engine_sync import create_sync_db_and_tables, sync_engine, DATABASE_URL_SYNC
# Import ALL models to ensure they are registered in SQLModel.metadata
from app.models.ap import AP
from app.models.audit_log import AuditLog
from app.models.bot_user import BotUser
from app.models.client import Client
from app.models.cpe import CPE
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.router import Router
from app.models.service import ClientService
from app.models.setting import Setting
from app.models.switch import Switch
from app.models.ticket import Ticket
from app.models.user import User
from app.models.zona import Zona, ZonaAutodoc
from app.models.stats import RouterStats, APStats, CPEStats, EventLog, DisconnectionEvent
from app.models.waiting_room import WaitingRoomConfig

# Configure logging
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def _is_sqlite_dialect() -> bool:
    """Check if the current database is SQLite."""
    return DATABASE_URL_SYNC.startswith("sqlite")


def bootstrap_system() -> None:
    """
    Idempotent Bootstrapping:
    1. Initializes DB tables (SQLModel).
    2. Initializes default data (dialect-aware).
    3. Checks if any user exists and creates admin if needed.
    """
    try:
        logger.info("🛠️ [Bootstrap] Initializing database schema...")
        
        # 1. Create SQLModel tables with concurrency protection
        from sqlalchemy.exc import OperationalError
        try:
            create_sync_db_and_tables()
        except OperationalError as e:
            if "already exists" in str(e):
                logger.warning(f"⚠️ [Bootstrap] Concurrency: Tables already exist ({e}). Continuing...")
            else:
                raise e

        # 2. Initialize default data (dialect-aware)
        if _is_sqlite_dialect():
            # Legacy SQLite initialization with raw SQL
            from app.db.init_db import setup_databases
            setup_databases()
            logger.info("✅ [Bootstrap] SQLite legacy schema initialized.")
        else:
            # PostgreSQL: Use ORM-based initialization
            from app.db.init_postgres import init_db
            with Session(sync_engine) as session:
                init_db(session)
            logger.info("✅ [Bootstrap] PostgreSQL ORM-based schema initialized.")

        # 3. Check for existing users
        with Session(sync_engine) as session:
            existing_user = session.exec(select(User)).first()
            if existing_user:
                logger.info("✅ [Bootstrap] System already initialized (users found). Skipping admin creation.")
                return

            # 4. Try Auto-Bootstrap from ENV
            logger.info("🌱 [Bootstrap] No users found. Checking Environment Variables for auto-create...")

            admin_email = settings.ADMIN_EMAIL
            admin_password = settings.ADMIN_PASSWORD
            admin_username = settings.ADMIN_USERNAME

            if admin_email and admin_password:
                start_auto_creation(session, admin_email, admin_username, admin_password)
            else:
                logger.warning("⚠️ [Bootstrap] No se encontró un usuario administrador ni variables predefinidas.")
                logger.info("👉 Para configurar el sistema, accede a la interfaz web en http://<tu-ip>/ o usa 'python launcher/main.py setup'.")
    except Exception as e:
        logger.critical(f"❌ [Bootstrap] Fatal error during initialization: {e}")
        raise e


def start_auto_creation(session: Session, email: str, username: str, password: str):
    """Creates the first superuser silently."""
    try:
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
        logger.info(f"🚀 [Bootstrap] Successfully created First Admin User: {email}")
    except Exception as e:
        logger.error(f"❌ [Bootstrap] Failed to create admin user: {e}")
        session.rollback()
        raise e
