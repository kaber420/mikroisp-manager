# app/auth.py
"""
⚠️  DEPRECATED MODULE - Compatibility layer for legacy endpoints
"""
import warnings

warnings.warn("app.auth is deprecated", DeprecationWarning, stacklevel=2)

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("FATAL: SECRET_KEY not configured")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: bool = False


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/login/access-token", auto_error=False
)


async def get_current_user(
    request: Request, token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """Compatibility wrapper - checks Bearer and cookies, works with UUID tokens"""
    if token is None:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if token is None:
        print("❌ No token found in header or cookie")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    print(f"🔍 Token found: {token[:20]}...")

    try:
        # FastAPI Users tokens include 'aud' claim, disable validation
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},  # Skip audience validation
        )
        user_id_or_username: str = payload.get("sub")
        print(f"✅ Token decoded. Sub: {user_id_or_username}")
        if not user_id_or_username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as e:
        print(f"❌ JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.db.engine_sync import sync_engine
    from sqlmodel import Session, select
    from app.models.user import User as SQLModelUser
    import uuid

    with Session(sync_engine) as session:
        try:
            user_uuid = uuid.UUID(user_id_or_username)
            stmt = select(SQLModelUser).where(SQLModelUser.id == user_uuid)
        except ValueError:
            stmt = select(SQLModelUser).where(
                SQLModelUser.username == user_id_or_username
            )

        db_user = session.exec(stmt).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        return User(
            username=db_user.username,
            email=db_user.email,
            disabled=not db_user.is_active,
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
