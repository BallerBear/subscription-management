"""Password hashing and JWT helpers. No database or FastAPI in here."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

import app.core.config  # noqa: F401  (makes sure .env has been loaded)

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALG = "HS256"
TOKEN_HOURS = 24
COOKIE_NAME = "access_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"  # true in production (https)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(user_id: int, role: str) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set. Copy .env.example to .env")
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": expires}, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError if the token is bad or expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
