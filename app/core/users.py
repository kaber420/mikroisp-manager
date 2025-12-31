# app/core/users.py
"""
FastAPI Users configuration and authentication setup.
Replaces manual JWT handling from app/auth.py with library-managed auth.
"""
import os
import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelper
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.user import User

# --- Configuration ---
SECRET = os.getenv("SECRET_KEY")
if not SECRET:
    raise RuntimeError("FATAL: SECRET_KEY not configured in .env")

ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token_v2"
ACCESS_TOKEN_LIFETIME_SECONDS = 28800  # 8 hours (standard work day)
APP_ENV = os.getenv("APP_ENV", "development")

# --- Authentication Transports ---
# 1. Bearer Token Transport (for API access via Authorization header)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# 2. Cookie Transport (for Web UI session management)
cookie_transport = CookieTransport(
    cookie_name=ACCESS_TOKEN_COOKIE_NAME,
    cookie_max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
    cookie_httponly=True,  # Prevent XSS attacks
    cookie_secure=(APP_ENV == "production"),  # HTTPS only in production
    cookie_samesite="lax",  # CSRF protection
)


# --- JWT Strategy ---
def get_jwt_strategy() -> JWTStrategy:
    """Returns JWT strategy for token generation and validation"""
    return JWTStrategy(secret=SECRET, lifetime_seconds=ACCESS_TOKEN_LIFETIME_SECONDS)


# --- Authentication Backends ---
# JWT Backend (Bearer token for API)
auth_backend_jwt = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Cookie Backend (HTTP-only cookie for Web UI)
auth_backend_cookie = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


# --- User Manager ---
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    User manager handles user lifecycle events and business logic.
    Customize this class to add custom user management behavior.
    """

    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after successful user registration"""
        print(f"✅ User registered: {user.username} ({user.email})")

    async def on_after_login(
        self, user: User, request: Optional[Request] = None, response=None
    ):
        """Called after successful login"""
        print(f"🔐 User logged in: {user.username}")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after password reset request"""
        print(f"🔑 Password reset requested for: {user.username}")


# --- Custom User Database Adapter (Username-based lookup) ---
class SQLAlchemyUserDatabaseByUsername(SQLAlchemyUserDatabase):
    """
    Custom SQLAlchemy user database adapter that looks up users by username
    instead of email. This allows the login form's 'username' field to be
    used for authentication instead of email.
    """

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Override: Look up user by username field instead of email.
        The 'email' parameter here is actually the value from the login form's
        'username' field (standard OAuth2 form field name).
        """
        from sqlalchemy import select

        statement = select(self.user_table).where(self.user_table.username == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


# --- Dependency Injectors ---
async def get_user_db(session: AsyncSession = Depends(get_session)):
    """
    Dependency to get the user database adapter.
    Uses custom SQLAlchemyUserDatabaseByUsername for username-based login.
    """
    yield SQLAlchemyUserDatabaseByUsername(session, User)


# --- Argon2 Password Helper ---
# Configure passlib to use Argon2 for password hashing
argon2_context = CryptContext(schemes=["argon2"], deprecated="auto")
password_helper = PasswordHelper(argon2_context)


async def get_user_manager(user_db=Depends(get_user_db)):
    """
    Dependency to get the user manager instance.
    Uses Argon2 for password hashing via PasswordHelper.
    """
    yield UserManager(user_db, password_helper)


# --- FastAPI Users Instance ---
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend_jwt, auth_backend_cookie],  # Support both auth methods
)

# --- Dependency Shortcuts ---
# These replace the old get_current_active_user from app/auth.py
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)


# --- Role-Based Access Control ---
# Valid role values (use lowercase strings for DB compatibility)
VALID_ROLES = ["admin", "technician", "billing"]


class RoleChecker:
    """
    Dependency class to check if the current user has one of the allowed roles.
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(RoleChecker(["admin"]))):
            ...
    """
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(current_active_user)) -> User:
        from fastapi import HTTPException, status
        
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(self.allowed_roles)}. Your role: {user.role}"
            )
        return user


# Pre-configured role checkers for common use cases
require_admin = RoleChecker(["admin"])
require_technician = RoleChecker(["admin", "technician"])
require_billing = RoleChecker(["admin", "billing"])

