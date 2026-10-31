from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import connection
from app.core.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = decode_access_token(credentials.credentials)
    with connection() as conn:
        user = conn.execute(
            """
            SELECT id, email, name, role, is_active
              FROM users
             WHERE id = %s
            """,
            (int(claims["sub"]),),
        ).fetchone()

    if user is None or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


def require_role(*allowed_roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do this")
        return user

    return dependency
