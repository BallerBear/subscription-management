"""FastAPI dependencies everyone imports.

    from app.core.deps import get_current_user, require_role

    @router.get("/x")
    def x(user = Depends(get_current_user)): ...

    @router.post("/y")
    def y(user = Depends(require_role("ADMIN", "STAFF"))): ...
"""

import jwt
from fastapi import Depends, Request

from app.core.db import connection
from app.core.errors import friendly_error
from app.core.security import COOKIE_NAME, decode_token


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise friendly_error("Please log in to continue", 401)
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise friendly_error("Your session has expired. Please log in again", 401)

    with connection() as conn:
        user = conn.execute(
            "SELECT id, email, name, role, is_active FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    if not user or not user["is_active"]:
        raise friendly_error("This account doesn't exist or has been disabled", 401)
    user.pop("is_active")
    return user


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise friendly_error("You don't have permission to do that", 403)
        return user

    return checker


require_staff = require_role("ADMIN", "STAFF")
require_admin = require_role("ADMIN")
