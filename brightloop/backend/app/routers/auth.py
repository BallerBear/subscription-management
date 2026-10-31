import re

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.db import connection, transaction
from app.core.deps import get_current_user
from app.core.errors import friendly_error
from app.core.security import (
    COOKIE_NAME,
    COOKIE_SECURE,
    TOKEN_HOURS,
    create_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Same pattern as the CHECK constraint in the database.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address")
    return value


class SignupIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    email: str
    company_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _clean_email(v)

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password is too long")
        return v


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return _clean_email(v)


def _set_cookie(response: Response, user: dict) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user["id"], user["role"]),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=TOKEN_HOURS * 3600,
        path="/",
    )


@router.post("/signup", status_code=201)
def signup(body: SignupIn, response: Response):
    # Public signup can only ever create a CUSTOMER (the database default).
    with transaction() as conn:
        taken = conn.execute("SELECT 1 FROM users WHERE lower(email) = %s", (body.email,)).fetchone()
        if taken:
            raise friendly_error("An account with this email already exists", 409, "email")
        user = conn.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) "
            "RETURNING id, email, name, role",
            (body.email, hash_password(body.password), body.name),
        ).fetchone()
        conn.execute(
            "INSERT INTO customers (user_id, company_name, contact_name, email) VALUES (%s, %s, %s, %s)",
            (user["id"], body.company_name, body.name, body.email),
        )
    _set_cookie(response, user)
    return user


@router.post("/login")
def login(body: LoginIn, response: Response):
    with connection() as conn:
        user = conn.execute(
            "SELECT id, email, name, role, password_hash, is_active FROM users WHERE lower(email) = %s",
            (body.email,),
        ).fetchone()
    # Same message for "no such user" and "wrong password" on purpose.
    if not user or not verify_password(body.password, user["password_hash"]):
        raise friendly_error("Incorrect email or password", 401)
    if not user["is_active"]:
        raise friendly_error("This account has been disabled. Contact support", 403)
    _set_cookie(response, user)
    return {k: user[k] for k in ("id", "email", "name", "role")}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
