"""Password hashing and JWT helpers shared by bearer and cookie sessions."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import COOKIE_SECURE, JWT_SECRET

JWT_ALG = "HS256"
TOKEN_ALGORITHM = JWT_ALG
TOKEN_HOURS = 12
TOKEN_LIFETIME = timedelta(hours=TOKEN_HOURS)
COOKIE_NAME = "brightloop_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, role: str) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set. Copy .env.example to .env")
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "iat": now, "exp": now + TOKEN_LIFETIME},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def create_access_token(user: dict) -> str:
    return create_token(int(user["id"]), str(user["role"]))


def decode_token(token: str) -> dict:
    """Decode a signed access token; invalid/expired tokens raise PyJWTError."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def decode_access_token(token: str) -> dict:
    """Compatibility helper used by bearer-token dependencies."""
    payload = decode_token(token)
    if not payload.get("sub") or not payload.get("role"):
        raise jwt.InvalidTokenError("Missing required token claims")
    return payload
