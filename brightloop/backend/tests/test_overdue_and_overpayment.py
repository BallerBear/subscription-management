"""Overdue follows the Time Machine; payments can never exceed the balance."""

from datetime import date

import psycopg
import pytest

from app.services.billing import run_billing
from app.services.clock import advance_clock
from app.services.payments import record_payment
from tests.billing_support import SKIP_REASON, build_world, connect, db_ready, reset_db, set_clock

pytestmark = pytest.mark.skipif(not db_ready(), reason=SKIP_REASON)

TOTAL = 236_000  # 2 x Rs 1,000.00 + 18% GST, in paise


@pytest.fixture()
def world():
    """Three subscriptions billed on 2026-01-15 with Net 15 terms (due 2026-01-30)."""
    conn = connect()
    admin_id = reset_db(conn)
    build_world(conn, subs=3, start=date(2026, 1, 15), term="Net 15")
    set_clock(conn, date(2026, 1, 15))
    run_billing(admin_id)
    yield conn, admin_id
    conn.close()


def _overdue_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM v_overdue_invoices").fetchone()["n"]


def test_nothing_is_overdue_before_the_due_date(world) -> None:
    conn, _ = world
    assert _overdue_count(conn) == 0


def test_invoices_become_overdue_after_advancing_the_clock(world) -> None:
    conn, admin_id = world

    advance_clock(admin_id, days=20)  # 2026-02-04: five days past the 2026-01-30 due date

    assert _overdue_count(conn) == 3
    row = conn.execute("SELECT days_past_due FROM v_overdue_invoices LIMIT 1").fetchone()
    assert row["days_past_due"] == 5


def test_paying_in_full_marks_the_invoice_paid_and_not_overdue(world) -> None:
    conn, admin_id = world
    invoice_id = conn.execute("SELECT id FROM invoices ORDER BY id LIMIT 1").fetchone()["id"]

    record_payment(admin_id, invoice_id, "UPI", TOTAL, date(2026, 1, 15))
    advance_clock(admin_id, days=20)

    status = conn.execute("SELECT status, amount_paid FROM invoices WHERE id = %s", (invoice_id,)).fetchone()
    assert status["status"] == "PAID"  # flipped by the database trigger, not by Python
    assert status["amount_paid"] == TOTAL
    assert _overdue_count(conn) == 2  # the other two are still overdue


def test_overpayment_is_rejected_and_nothing_is_recorded(world) -> None:
    conn, admin_id = world
    invoice_id = conn.execute("SELECT id FROM invoices ORDER BY id LIMIT 1").fetchone()["id"]

    with pytest.raises(psycopg.Error):  # raised by the database, not by our Python
        record_payment(admin_id, invoice_id, "CARD", TOTAL + 1, date(2026, 1, 15))

    assert conn.execute("SELECT COUNT(*) AS n FROM payments").fetchone()["n"] == 0
    assert conn.execute("SELECT amount_paid FROM invoices WHERE id = %s", (invoice_id,)).fetchone()["amount_paid"] == 0


def test_partial_payments_add_up_and_the_last_one_cannot_overshoot(world) -> None:
    conn, admin_id = world
    invoice_id = conn.execute("SELECT id FROM invoices ORDER BY id LIMIT 1").fetchone()["id"]

    record_payment(admin_id, invoice_id, "CASH", 100_000, date(2026, 1, 15))
    with pytest.raises(psycopg.Error):
        record_payment(admin_id, invoice_id, "CASH", TOTAL - 100_000 + 1, date(2026, 1, 15))
    record_payment(admin_id, invoice_id, "CASH", TOTAL - 100_000, date(2026, 1, 15))

    row = conn.execute("SELECT status, amount_paid FROM invoices WHERE id = %s", (invoice_id,)).fetchone()
    assert (row["status"], row["amount_paid"]) == ("PAID", TOTAL)
