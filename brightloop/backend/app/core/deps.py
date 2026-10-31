"""Authentication and role dependencies.

Both the browser's HttpOnly cookie and API bearer tokens are supported.
The database remains authoritative for account status and role changes.
"""

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import connection
from app.core.errors import friendly_error
from app.core.security import COOKIE_NAME, decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    token = credentials.credentials if credentials is not None else request.cookies.get(COOKIE_NAME)
    if not token:
        raise friendly_error("Please log in to continue", 401)

    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
        if not payload.get("role"):
            raise ValueError("Missing role claim")
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise friendly_error("Your session has expired. Please log in again", 401)

    with connection() as conn:
        user = conn.execute(
            "SELECT id, email, name, role, is_active FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()

    if not user or not user["is_active"]:
        raise friendly_error("This account doesn't exist or has been disabled", 401)
    return user


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise friendly_error("You don't have permission to do that", 403)
        return user

    return checker


require_staff = require_role("ADMIN", "STAFF")
require_admin = require_role("ADMIN")
