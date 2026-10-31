import secrets

from fastapi import APIRouter, Depends, Response, status

from app.core.config import ADMIN_BOOTSTRAP_TOKEN
from app.core.db import connection, transaction
from app.core.deps import get_current_user, require_role
from app.core.errors import friendly_error
from app.core.security import (
    COOKIE_NAME,
    COOKIE_SECURE,
    TOKEN_HOURS,
    create_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import BootstrapAdminRequest, LoginRequest, RegisterRequest, StaffCreateRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


def _auth_response(user: dict) -> dict:
    public = _public_user(user)
    return {
        "user": public,
        **public,
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }


def _set_cookie(response: Response, user: dict) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=TOKEN_HOURS * 3600,
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
@router.post("/signup", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def register(payload: RegisterRequest, response: Response) -> dict:
    """Create a customer profile. /signup is retained as a compatibility alias."""
    with transaction() as conn:
        taken = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = lower(%s)",
            (payload.email,),
        ).fetchone()
        if taken:
            raise friendly_error("An account with this email already exists", 409, "email")

        user = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, role)
            VALUES (%s, %s, %s, 'CUSTOMER')
            RETURNING id, email, name, role
            """,
            (payload.email, hash_password(payload.password), payload.name),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO customers (user_id, company_name, contact_name, email, phone)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user["id"],
                payload.company_name,
                payload.contact_name or payload.name,
                payload.email,
                payload.phone,
            ),
        )

    _set_cookie(response, user)
    return _auth_response(user)


@router.post("/login")
def login(payload: LoginRequest, response: Response) -> dict:
    with connection() as conn:
        user = conn.execute(
            """
            SELECT id, email, name, role, password_hash, is_active
              FROM users
             WHERE lower(email) = lower(%s)
            """,
            (payload.email,),
        ).fetchone()

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise friendly_error("Incorrect email or password", 401)
    if not user["is_active"]:
        raise friendly_error("This account has been disabled. Contact support", 403)

    _set_cookie(response, user)
    return _auth_response(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return _public_user(user)


@router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdminRequest, response: Response) -> dict:
    if not ADMIN_BOOTSTRAP_TOKEN or not secrets.compare_digest(payload.bootstrap_token, ADMIN_BOOTSTRAP_TOKEN):
        raise friendly_error("Admin bootstrap is not enabled or the token is incorrect", 403)

    with transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(728194)")
        exists = conn.execute("SELECT 1 FROM users WHERE role = 'ADMIN' LIMIT 1").fetchone()
        if exists:
            raise friendly_error("An admin account already exists", 409)
        user = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, role)
            VALUES (%s, %s, %s, 'ADMIN')
            RETURNING id, email, name, role
            """,
            (payload.email, hash_password(payload.password), payload.name),
        ).fetchone()

    _set_cookie(response, user)
    return _auth_response(user)


@router.post("/staff", status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreateRequest,
    admin: dict = Depends(require_role("ADMIN")),
) -> dict:
    with transaction(user_id=admin["id"]) as conn:
        user = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, role)
            VALUES (%s, %s, %s, 'STAFF')
            RETURNING id, email, name, role
            """,
            (payload.email, hash_password(payload.password), payload.name),
        ).fetchone()
    return _public_user(user)
