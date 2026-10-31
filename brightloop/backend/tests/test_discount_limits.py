"""A discount with usage_limit = 10 across 40 subscriptions applies exactly 10 times."""

from datetime import date

import pytest

from app.services.billing import run_billing
from tests.billing_support import (
    SKIP_REASON,
    build_world,
    connect,
    db_ready,
    reset_db,
    set_clock,
)

pytestmark = pytest.mark.skipif(not db_ready(), reason=SKIP_REASON)

SUBS = 40
LIMIT = 10


@pytest.fixture()
def world():
    conn = connect()
    admin_id = reset_db(conn)
    sub_ids = build_world(conn, subs=SUBS, start=date(2026, 1, 15))
    # 10% off the whole subscription, attached to ALL 40, but only 10 uses allowed.
    discount_id = conn.execute(
        "INSERT INTO discounts (name, type, value, scope, start_date, usage_limit) "
        "VALUES ('Launch offer', 'PERCENT', 1000, 'SUBSCRIPTION', '2026-01-01', %s) RETURNING id",
        (LIMIT,),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO subscription_discounts (subscription_id, discount_id) "
        "SELECT unnest(%s::bigint[]), %s",
        (sub_ids, discount_id),
    )
    set_clock(conn, date(2026, 1, 15))
    yield conn, admin_id, discount_id
    conn.close()


def test_usage_limit_of_ten_discounts_exactly_ten_invoices(world) -> None:
    conn, admin_id, discount_id = world

    result = run_billing(admin_id)

    assert result["created"] == SUBS  # every subscription is still billed

    redemptions = conn.execute(
        "SELECT COUNT(*) AS n FROM discount_redemptions WHERE discount_id = %s", (discount_id,)
    ).fetchone()["n"]
    discounted = conn.execute("SELECT COUNT(*) AS n FROM invoices WHERE discount_total > 0").fetchone()["n"]
    times_used = conn.execute("SELECT times_used FROM discounts WHERE id = %s", (discount_id,)).fetchone()["times_used"]

    assert redemptions == LIMIT
    assert discounted == LIMIT
    assert times_used == LIMIT


def test_discount_amount_is_ten_percent_of_the_subtotal(world) -> None:
    conn, admin_id, _ = world
    run_billing(admin_id)

    row = conn.execute(
        "SELECT subtotal, discount_total FROM invoices WHERE discount_total > 0 LIMIT 1"
    ).fetchone()
    # 10% of Rs 2,000.00 = Rs 200.00
    assert row["subtotal"] == 200_000
    assert row["discount_total"] == 20_000


def test_a_second_run_does_not_use_the_discount_again(world) -> None:
    conn, admin_id, discount_id = world
    run_billing(admin_id)
    run_billing(admin_id)

    times_used = conn.execute("SELECT times_used FROM discounts WHERE id = %s", (discount_id,)).fetchone()["times_used"]
    assert times_used == LIMIT
