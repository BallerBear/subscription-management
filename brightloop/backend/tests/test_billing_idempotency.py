"""The Time Machine promise: nothing is ever billed twice.

Real services, real Postgres. See billing_support.py for how to run these.
"""

from datetime import date

import pytest

from app.services.billing import run_billing
from tests.billing_support import (
    SKIP_REASON,
    build_world,
    connect,
    db_ready,
    invoice_count,
    reset_db,
    set_clock,
)

pytestmark = pytest.mark.skipif(not db_ready(), reason=SKIP_REASON)

SUBS = 40


@pytest.fixture()
def world():
    """A clean database with 40 ACTIVE monthly subscriptions that start on 2026-01-15."""
    conn = connect()
    admin_id = reset_db(conn)
    build_world(conn, subs=SUBS, start=date(2026, 1, 15))
    yield conn, admin_id
    conn.close()


def test_running_billing_twice_creates_nothing_the_second_time(world) -> None:
    conn, admin_id = world
    set_clock(conn, date(2026, 1, 15))  # the first billing day

    first = run_billing(admin_id)
    second = run_billing(admin_id)

    assert first["created"] == SUBS
    assert second["created"] == 0
    assert second["skipped"] == 0
    assert second["up_to_date"] == SUBS  # "0 new invoices. 40 subscriptions already up to date."
    assert invoice_count(conn) == SUBS  # still 40, not 80


def test_long_clock_jump_catches_up_every_missed_period_exactly_once(world) -> None:
    conn, admin_id = world
    set_clock(conn, date(2026, 4, 20))  # Jan 15, Feb 15, Mar 15 and Apr 15 are all due

    first = run_billing(admin_id)
    again = run_billing(admin_id)

    assert first["created"] == SUBS * 4
    assert again["created"] == 0

    # Each (subscription, period) pair exists exactly once.
    rows = conn.execute(
        "SELECT subscription_id, period_start, COUNT(*) AS n FROM invoices "
        "GROUP BY subscription_id, period_start HAVING COUNT(*) > 1"
    ).fetchall()
    assert rows == []

    periods = conn.execute(
        "SELECT DISTINCT period_start FROM invoices ORDER BY period_start"
    ).fetchall()
    assert [r["period_start"] for r in periods] == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]

    # Billing advanced every subscription to the next unbilled period.
    next_dates = {r["next_billing_date"] for r in conn.execute("SELECT next_billing_date FROM subscriptions")}
    assert next_dates == {date(2026, 5, 15)}


def test_totals_come_from_the_database_not_python(world) -> None:
    """2 x Rs 1,000.00 = Rs 2,000.00 + 18% GST (Rs 360.00) = Rs 2,360.00, in paise."""
    conn, admin_id = world
    set_clock(conn, date(2026, 1, 15))
    run_billing(admin_id)

    row = conn.execute("SELECT subtotal, tax_total, total, status FROM invoices LIMIT 1").fetchone()
    assert (row["subtotal"], row["tax_total"], row["total"]) == (200_000, 36_000, 236_000)
    assert row["status"] == "CONFIRMED"  # auto_confirm defaults to True
