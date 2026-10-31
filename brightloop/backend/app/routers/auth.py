import secrets

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import ADMIN_BOOTSTRAP_TOKEN
from app.core.db import connection, transaction
from app.core.deps import get_current_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import (
    BootstrapAdminRequest, LoginRequest, RegisterRequest, StaffCreateRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict:
    with transaction() as conn:
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
            (user["id"], payload.company_name, payload.contact_name, payload.email, payload.phone),
        )
    return {"user": _public_user(user), "access_token": create_access_token(user), "token_type": "bearer"}


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    with connection() as conn:
        user = conn.execute(
            """
            SELECT id, email, name, role, password_hash, is_active
              FROM users
             WHERE lower(email) = lower(%s)
            """,
            (payload.email.strip(),),
        ).fetchone()

    if user is None or not user["is_active"] or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"user": _public_user(user), "access_token": create_access_token(user), "token_type": "bearer"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return _public_user(user)


@router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdminRequest) -> dict:
    if not ADMIN_BOOTSTRAP_TOKEN or not secrets.compare_digest(payload.bootstrap_token, ADMIN_BOOTSTRAP_TOKEN):
        raise HTTPException(status_code=403, detail="Admin bootstrap is not enabled or the token is incorrect")

    with transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(728194)")
        exists = conn.execute("SELECT 1 FROM users WHERE role = 'ADMIN' LIMIT 1").fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="An admin account already exists")
        user = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, role)
            VALUES (%s, %s, %s, 'ADMIN')
            RETURNING id, email, name, role
            """,
            (payload.email, hash_password(payload.password), payload.name),
        ).fetchone()
    return {"user": _public_user(user), "access_token": create_access_token(user), "token_type": "bearer"}


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
