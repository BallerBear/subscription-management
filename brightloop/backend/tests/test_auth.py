"""Auth flow tests: signup, login, /me, logout, deactivation, role checks.

These hit a REAL Postgres through FastAPI's TestClient (no mocks), because the
interesting behaviour lives in the database: the unique email index, the
customers row created with the user, and is_active being re-read per request.

Run against a LOCAL database only:

    docker run -d --rm --name bl-test-pg -e POSTGRES_PASSWORD=t -e POSTGRES_DB=bl -p 55432:5432 postgres:16
    DATABASE_URL=postgresql://postgres:t@localhost:55432/bl python database/migrate.py
    DATABASE_URL=postgresql://postgres:t@localhost:55432/bl pytest tests/test_auth.py

If DATABASE_URL points anywhere that is not localhost the whole file is skipped,
so nobody litters the shared Supabase database by accident.
"""

import os
import uuid
from urllib.parse import urlparse

import psycopg
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import config
from app.core.deps import require_role
from app.core.errors import register_handlers
from app.core.security import COOKIE_NAME, hash_password
from app.main import app

GOOD_PASSWORD = "Str0ng!Passw"
TEST_DOMAIN = "@authtest.example.com"  # every row we create ends with this, so cleanup is exact


def _is_local(url: str) -> bool:
    return (urlparse(url).hostname or "") in ("localhost", "127.0.0.1", "::1")


def _db_ready() -> bool:
    if not _is_local(config.DATABASE_URL):
        return False
    try:
        with psycopg.connect(config.DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1 FROM users LIMIT 1")  # also proves migrations ran
        return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(
    not _db_ready(),
    reason="Needs a LOCAL Postgres with migrations applied (see the docstring at the top of this file)",
)


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    """Remove every row this file creates, before and after the module runs."""

    def wipe():
        with psycopg.connect(config.DATABASE_URL) as conn:
            conn.execute(
                "DELETE FROM customers WHERE user_id IN (SELECT id FROM users WHERE email LIKE %s)",
                (f"%{TEST_DOMAIN}",),
            )
            conn.execute("DELETE FROM users WHERE email LIKE %s", (f"%{TEST_DOMAIN}",))

    wipe()
    yield
    wipe()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _email(prefix: str = "u") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}{TEST_DOMAIN}"


def _signup_body(**overrides) -> dict:
    body = {"name": "Test User", "email": _email(), "company_name": "Acme Ltd", "password": GOOD_PASSWORD}
    body.update(overrides)
    return body


def _make_user(role: str, is_active: bool = True) -> dict:
    """Insert a user directly (public signup can only make CUSTOMERs)."""
    email = _email(role.lower())
    with psycopg.connect(config.DATABASE_URL) as conn:
        row = conn.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (email, hash_password(GOOD_PASSWORD), f"{role.title()} Person", role, is_active),
        ).fetchone()
    return {"id": row[0], "email": email}


def _db_one(sql: str, params: tuple):
    with psycopg.connect(config.DATABASE_URL) as conn:
        return conn.execute(sql, params).fetchone()


# ---------------------------------------------------------------- signup


def test_signup_creates_customer_user_and_linked_customer_row(client):
    body = _signup_body()
    r = client.post("/auth/signup", json=body)

    assert r.status_code == 201
    assert r.json()["role"] == "CUSTOMER"
    assert "password" not in r.json() and "password_hash" not in r.json()

    # The user AND the customers row must exist, linked, from one transaction.
    row = _db_one(
        "SELECT u.role, c.company_name, c.contact_name FROM users u "
        "JOIN customers c ON c.user_id = u.id WHERE u.email = %s",
        (body["email"],),
    )
    assert row == ("CUSTOMER", "Acme Ltd", "Test User")


def test_signup_cannot_choose_a_role(client):
    """Mass-assignment check: a sneaky `role` in the body must be ignored."""
    body = _signup_body(role="ADMIN")
    r = client.post("/auth/signup", json=body)

    assert r.status_code == 201
    assert r.json()["role"] == "CUSTOMER"


def test_signup_stores_a_bcrypt_hash_not_the_password(client):
    body = _signup_body()
    client.post("/auth/signup", json=body)

    (stored,) = _db_one("SELECT password_hash FROM users WHERE email = %s", (body["email"],))
    assert stored != body["password"]
    assert stored.startswith("$2")  # bcrypt prefix


def test_signup_sets_httponly_cookie_and_logs_you_in(client):
    r = client.post("/auth/signup", json=_signup_body())

    set_cookie = r.headers["set-cookie"]
    assert f"{COOKIE_NAME}=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    assert client.get("/auth/me").status_code == 200  # the TestClient kept the cookie


def test_bearer_access_token_is_accepted_without_a_cookie(client):
    body = _signup_body()
    signup = client.post("/auth/signup", json=body)
    token = signup.json()["access_token"]
    client.cookies.clear()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == body["email"]


def test_signup_lowercases_email(client):
    body = _signup_body(email=f"MiXeD-{uuid.uuid4().hex[:8]}{TEST_DOMAIN}".upper())
    r = client.post("/auth/signup", json=body)

    assert r.status_code == 201
    assert r.json()["email"] == body["email"].lower()


def test_signup_duplicate_email_is_409_even_with_different_case(client):
    body = _signup_body()
    assert client.post("/auth/signup", json=body).status_code == 201

    again = client.post("/auth/signup", json={**body, "email": body["email"].upper()})

    assert again.status_code == 409
    assert again.json()["message"] == "An account with this email already exists"
    assert "email" in again.json()["fields"]  # so the form can show it under the field


def test_signup_validation_errors_name_each_field(client):
    r = client.post(
        "/auth/signup",
        json={"name": "A", "email": "not-an-email", "company_name": "", "password": "short"},
    )

    assert r.status_code == 422
    fields = r.json()["fields"]
    assert {"name", "email", "company_name", "password"} <= set(fields)
    assert fields["email"] == "Enter a valid email address"


def test_signup_rejects_missing_fields(client):
    r = client.post("/auth/signup", json={})

    assert r.status_code == 422
    assert set(r.json()["fields"]) == {"name", "email", "company_name", "password"}


@pytest.mark.parametrize(
    "password",
    [
        "A" * 73,  # one character over bcrypt's 72-byte limit
        "é" * 40,  # 40 characters but 80 bytes: passes a length check, breaks bcrypt
    ],
)
def test_signup_rejects_passwords_bcrypt_cannot_hash(client, password):
    r = client.post("/auth/signup", json=_signup_body(password=password))

    assert r.status_code == 422
    assert "password" in r.json()["fields"]


def test_signup_accepts_the_72_byte_limit(client):
    r = client.post("/auth/signup", json=_signup_body(password="Aa!" * 24))  # exactly 72 bytes

    assert r.status_code == 201


@pytest.mark.parametrize(
    "password",
    ["alllowercase1!", "ALLUPPERCASE1!", "NoSpecialChar1", "Abcdef1!"],  # no upper / no lower / no special / only 8 chars (spec: more than 8)
)
def test_signup_enforces_password_complexity(client, password):
    r = client.post("/auth/signup", json=_signup_body(password=password))

    assert r.status_code == 422
    assert "password" in r.json()["fields"]


# ---------------------------------------------------------------- login


def test_login_success_returns_user_and_sets_cookie(client):
    body = _signup_body()
    client.post("/auth/signup", json=body)
    client.cookies.clear()

    r = client.post("/auth/login", json={"email": body["email"], "password": GOOD_PASSWORD})

    assert r.status_code == 200
    assert r.json()["email"] == body["email"]
    assert r.json()["role"] == "CUSTOMER"
    assert "password_hash" not in r.json()
    assert client.get("/auth/me").json()["email"] == body["email"]


def test_login_email_is_case_insensitive(client):
    body = _signup_body()
    client.post("/auth/signup", json=body)

    r = client.post("/auth/login", json={"email": body["email"].upper(), "password": GOOD_PASSWORD})

    assert r.status_code == 200


def test_login_wrong_password_and_unknown_email_give_the_same_answer(client):
    """If the messages differed, an attacker could discover which emails have accounts."""
    body = _signup_body()
    client.post("/auth/signup", json=body)
    client.cookies.clear()

    wrong_pw = client.post("/auth/login", json={"email": body["email"], "password": "Wrong!Pass1"})
    no_user = client.post("/auth/login", json={"email": _email("ghost"), "password": "Wrong!Pass1"})

    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()
    assert COOKIE_NAME not in wrong_pw.headers.get("set-cookie", "")


def test_login_with_malformed_email_is_422(client):
    r = client.post("/auth/login", json={"email": "nope", "password": "x"})

    assert r.status_code == 422
    assert "email" in r.json()["fields"]


def test_login_disabled_account_is_refused(client):
    user = _make_user("STAFF", is_active=False)

    r = client.post("/auth/login", json={"email": user["email"], "password": GOOD_PASSWORD})

    assert r.status_code == 403
    assert COOKIE_NAME not in r.headers.get("set-cookie", "")


@pytest.mark.parametrize("role", ["ADMIN", "STAFF"])
def test_login_returns_the_real_role_for_staff_and_admin(client, role):
    """The frontend uses this role to pick /admin, /staff or /portal."""
    user = _make_user(role)

    r = client.post("/auth/login", json={"email": user["email"], "password": GOOD_PASSWORD})

    assert r.status_code == 200
    assert r.json()["role"] == role


# ---------------------------------------------------------------- /me and logout


def test_me_without_cookie_is_401(client):
    r = client.get("/auth/me")

    assert r.status_code == 401
    assert r.json()["message"] == "Please log in to continue"


def test_me_with_garbage_token_is_401(client):
    client.cookies.set(COOKIE_NAME, "not.a.jwt")

    assert client.get("/auth/me").status_code == 401


def test_me_rejects_alg_none_forged_token(client):
    """Classic attack: an unsigned token claiming to be user 1. Needs algorithms=['HS256'] to fail."""
    forged = "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIiwicm9sZSI6IkFETUlOIn0."
    client.cookies.set(COOKIE_NAME, forged)

    assert client.get("/auth/me").status_code == 401


def test_me_rejects_token_signed_with_the_wrong_secret(client):
    import jwt

    token = jwt.encode({"sub": "1", "role": "ADMIN"}, "some-other-secret-32-bytes-long-xxxx", algorithm="HS256")
    client.cookies.set(COOKIE_NAME, token)

    assert client.get("/auth/me").status_code == 401


def test_me_rejects_expired_token(client):
    import jwt
    from datetime import datetime, timedelta, timezone

    from app.core.security import JWT_SECRET

    user = _make_user("STAFF")
    expired = jwt.encode(
        {"sub": str(user["id"]), "role": "STAFF", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET,
        algorithm="HS256",
    )
    client.cookies.set(COOKIE_NAME, expired)

    assert client.get("/auth/me").status_code == 401


def test_logout_clears_the_cookie_and_ends_the_session(client):
    client.post("/auth/signup", json=_signup_body())
    assert client.get("/auth/me").status_code == 200

    r = client.post("/auth/logout")

    assert r.status_code == 200
    assert "max-age=0" in r.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 401


def test_deactivating_a_user_kills_their_live_session_immediately(client):
    """get_current_user re-reads the row on every request, so there is no 'valid for 24h' loophole."""
    body = _signup_body()
    client.post("/auth/signup", json=body)
    assert client.get("/auth/me").status_code == 200

    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("UPDATE users SET is_active = false WHERE email = %s", (body["email"],))

    assert client.get("/auth/me").status_code == 401


def test_role_change_in_the_database_beats_the_role_in_the_token(client):
    """The JWT says CUSTOMER, the DB now says STAFF: /me must trust the database."""
    body = _signup_body()
    client.post("/auth/signup", json=body)

    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("UPDATE users SET role = 'STAFF' WHERE email = %s", (body["email"],))

    assert client.get("/auth/me").json()["role"] == "STAFF"


# ---------------------------------------------------------------- require_role


@pytest.fixture
def guarded_client():
    """A tiny app with one route per guard, so we can test require_role before the real routers exist."""
    mini = FastAPI()
    register_handlers(mini)

    @mini.get("/admin-only")
    def admin_only(user=Depends(require_role("ADMIN"))):
        return {"role": user["role"]}

    @mini.get("/staff-area")
    def staff_area(user=Depends(require_role("ADMIN", "STAFF"))):
        return {"role": user["role"]}

    with TestClient(mini) as c:
        yield c


def _login(c: TestClient, user: dict) -> None:
    assert c.post("/auth/login", json={"email": user["email"], "password": GOOD_PASSWORD}).status_code == 200


@pytest.fixture
def login_as(guarded_client):
    """Log in through the real app, then copy the cookie to the mini app."""

    def _do(role: str) -> TestClient:
        user = _make_user(role)
        with TestClient(app) as real:
            _login(real, user)
            guarded_client.cookies.set(COOKIE_NAME, real.cookies[COOKIE_NAME])
        return guarded_client

    return _do


def test_require_role_anonymous_gets_401(guarded_client):
    assert guarded_client.get("/admin-only").status_code == 401


@pytest.mark.parametrize(
    "role, path, expected",
    [
        ("ADMIN", "/admin-only", 200),
        ("STAFF", "/admin-only", 403),  # admin is NOT implied for staff routes, and staff is not admin
        ("CUSTOMER", "/admin-only", 403),
        ("ADMIN", "/staff-area", 200),
        ("STAFF", "/staff-area", 200),
        ("CUSTOMER", "/staff-area", 403),
    ],
)
def test_require_role_matrix(login_as, role, path, expected):
    c = login_as(role)

    r = c.get(path)

    assert r.status_code == expected
    if expected == 403:
        assert r.json()["message"] == "You don't have permission to do that"


# ---------------------------------------------------------------- known gaps from the spec


def test_cookie_is_named_brightloop_token(client):
    r = client.post("/auth/signup", json=_signup_body())

    assert "brightloop_token=" in r.headers["set-cookie"]


@pytest.mark.xfail(strict=True, reason="KNOWN GAP (CLAUDE.md s9): forgot-password / reset-password not built yet.")
def test_forgot_password_never_reveals_whether_the_email_exists(client):
    known = _signup_body()
    client.post("/auth/signup", json=known)

    a = client.post("/auth/forgot-password", json={"email": known["email"]})
    b = client.post("/auth/forgot-password", json={"email": _email("ghost")})

    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


@pytest.mark.xfail(strict=True, reason="KNOWN GAP (CLAUDE.md s9): POST /users/staff not built yet.")
def test_only_admin_can_create_staff():
    payload = {"name": "New Staff", "email": _email("newstaff"), "password": GOOD_PASSWORD}

    with TestClient(app) as staff_client, TestClient(app) as admin_client:
        _login(staff_client, _make_user("STAFF"))
        _login(admin_client, _make_user("ADMIN"))

        assert staff_client.post("/users/staff", json=payload).status_code == 403
        assert admin_client.post("/users/staff", json=payload).status_code == 201
