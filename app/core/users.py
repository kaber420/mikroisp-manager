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
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.user import User

# --- Configuration ---
SECRET = os.getenv("SECRET_KEY")
if not SECRET:
    raise RuntimeError("FATAL: SECRET_KEY not configured in .env")

ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"
ACCESS_TOKEN_LIFETIME_SECONDS = 1800  # 30 minutes
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


# --- Dependency Injectors ---
async def get_user_db(session: AsyncSession = Depends(get_session)):
    """
    Dependency to get the user database adapter.
    Uses SQLAlchemyUserDatabase for FastAPI Users v15+ with async sessions.
    """
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    """
    Dependency to get the user manager instance.
    """
    yield UserManager(user_db)


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
