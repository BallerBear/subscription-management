"""Shared helpers for the billing / discount / payment tests.

These tests call the REAL services against a REAL Postgres (no mocks), because
the guarantees we want to prove ("never billed twice", "a discount applies at
most usage_limit times", "no overpayment") are enforced partly by the database.

SAFETY: the tests wipe every table. So they only run when DATABASE_URL points
at localhost AND the database name contains "test". A real dev database, or
the shared Supabase one, can never be wiped by accident.

    docker run -d --rm --name bl-test-pg -e POSTGRES_PASSWORD=t \
        -e POSTGRES_DB=brightloop_test -p 55432:5432 postgres:16-alpine
    export DATABASE_URL=postgresql://postgres:t@localhost:55432/brightloop_test
    python database/migrate.py
    pytest
"""

from datetime import date
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from app.core import config


def is_safe_test_db(url: str) -> bool:
    """True only for a localhost database whose name contains 'test'."""
    parsed = urlparse(url)
    local = (parsed.hostname or "") in ("localhost", "127.0.0.1", "::1")
    return local and "test" in parsed.path.lower()


def db_ready() -> bool:
    """Safe target AND migrations applied. Used by the skip marker in each test file."""
    if not is_safe_test_db(config.DATABASE_URL):
        return False
    try:
        with psycopg.connect(config.DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1 FROM invoices LIMIT 1")
        return True
    except psycopg.Error:
        return False


SKIP_REASON = (
    "Needs a LOCAL test database (name contains 'test') with migrations applied; "
    "see the docstring at the top of tests/billing_support.py"
)

# Tables that hold fixed reference data from the migrations; everything else is wiped.
_KEEP = ("payment_terms", "status_transitions", "app_clock", "schema_migrations")


def connect() -> psycopg.Connection:
    assert is_safe_test_db(config.DATABASE_URL), "refusing to touch a non-test database"
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=True)


def reset_db(conn: psycopg.Connection) -> int:
    """Empty every data table and return a fresh admin user id (needed for 'who did it')."""
    tables = [
        r["tablename"]
        for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        if r["tablename"] not in _KEEP
    ]
    names = ", ".join(f'"{t}"' for t in tables)  # names come from pg_tables, not user input
    conn.execute(f"TRUNCATE {names} RESTART IDENTITY CASCADE")
    return conn.execute(
        "INSERT INTO users (email, password_hash, name, role) "
        "VALUES ('admin@billing-test.example.com', 'x', 'Test Admin', 'ADMIN') RETURNING id"
    ).fetchone()["id"]


def set_clock(conn: psycopg.Connection, today: date) -> None:
    conn.execute("UPDATE app_clock SET today = %s", (today,))


def build_world(
    conn: psycopg.Connection,
    *,
    subs: int,
    start: date,
    period: str = "MONTHLY",
    term: str = "Net 15",
    unit_price: int = 100_000,  # Rs 1,000.00 in paise
    quantity: int = 2,
) -> list[int]:
    """Create `subs` ACTIVE subscriptions (one customer each), all billed from `start`.

    Everything is set-based (INSERT ... SELECT), so it costs a handful of
    queries no matter how many subscriptions we ask for.
    Returns the subscription ids.
    """
    tax_id = conn.execute(
        "INSERT INTO taxes (name, rate_bps) VALUES ('GST 18%%', 1800) RETURNING id"
    ).fetchone()["id"]
    product_id = conn.execute(
        "INSERT INTO products (name, type, sales_price, tax_id) "
        "VALUES ('Test Suite', 'SOFTWARE', %s, %s) RETURNING id",
        (unit_price, tax_id),
    ).fetchone()["id"]
    plan_id = conn.execute(
        "INSERT INTO plans (name, price, billing_period, available_from) "
        "VALUES ('Test plan', 0, %s, '2020-01-01') RETURNING id",
        (period,),
    ).fetchone()["id"]
    term_id = conn.execute("SELECT id FROM payment_terms WHERE name = %s", (term,)).fetchone()["id"]

    conn.execute(
        "INSERT INTO customers (company_name, contact_name, email) "
        "SELECT 'Customer ' || n, 'Contact ' || n, 'customer' || n || '@example.com' "
        "FROM generate_series(1, %s) AS n",
        (subs,),
    )
    ids = [
        r["id"]
        for r in conn.execute(
            "INSERT INTO subscriptions (customer_id, plan_id, payment_term_id, start_date, expiry_date) "
            "SELECT c.id, %s, %s, %s, (%s::date + interval '3 years')::date FROM customers c "
            "ORDER BY c.id RETURNING id",
            (plan_id, term_id, start, start),
        )
    ]
    conn.execute(
        "INSERT INTO subscription_lines "
        "(subscription_id, product_id, description, quantity, unit_price, tax_name, tax_rate_bps) "
        "SELECT id, %s, 'Test Suite', %s, %s, 'GST 18%%', 1800 FROM subscriptions",
        (product_id, quantity, unit_price),
    )
    # The database only allows legal status moves, so walk the real path.
    conn.execute("UPDATE subscriptions SET status = 'QUOTATION'")
    conn.execute("UPDATE subscriptions SET status = 'CONFIRMED'")
    conn.execute("UPDATE subscriptions SET status = 'ACTIVE', next_billing_date = start_date")
    return ids


def invoice_count(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"]
