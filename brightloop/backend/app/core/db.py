"""Database access: one shared connection pool and a transaction helper.

Everything that touches the database goes through `transaction()` (writes) or
`connection()` (read-only), so the pool size cap and the "who did this"
bookkeeping live in exactly one place.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import DATABASE_URL

# Capped at 5: four teammates share one free-tier database. open=False means
# importing this module does not connect; the pool opens on first use.
def _new_pool() -> ConnectionPool:
    return ConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},  # rows come back as dicts: row["total"]
        open=False,
    )


_pool = _new_pool()


def _ensure_open() -> None:
    if _pool.closed:
        _pool.open()


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Borrow a connection for reads. Commits on success, rolls back on error."""
    _ensure_open()
    with _pool.connection() as conn:
        yield conn


@contextmanager
def transaction(user_id: int | None = None) -> Iterator[psycopg.Connection]:
    """One atomic unit of work. Pass user_id on EVERY write.

    The triggers in 001_init.sql read `app.user_id` to fill changed_by in
    subscription_events and audit_log. `set_config(..., true)` makes the value
    local to this transaction, so it can never leak to the next request that
    reuses the pooled connection.
    """
    with connection() as conn:
        if user_id is not None:
            conn.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
        yield conn


def get_today(conn: psycopg.Connection):
    """The system's 'today' (Time Machine). Never use date.today() for business logic."""
    return conn.execute("SELECT today FROM app_clock").fetchone()["today"]


def close_pool() -> None:
    """Call on app shutdown."""
    global _pool
    if not _pool.closed:
        _pool.close()
        # A closed psycopg pool can never be reopened. Swap in a fresh, unopened
        # one so the app (or a test that starts/stops the app repeatedly) can keep
        # working; _ensure_open() opens it again on the next query.
        _pool = _new_pool()
