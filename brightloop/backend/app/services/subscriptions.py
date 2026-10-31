"""Subscriptions: list, detail, create, lifecycle moves, discounts."""

from datetime import date

from app.core.db import connection, transaction
from app.services.common import RuleError, not_found, paged


def list_subscriptions(
    status: str | None = None,
    customer_id: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    conds, params = [], []
    if status:
        conds.append("s.status = %s::subscription_status_t")
        params.append(status)
    if customer_id:
        conds.append("s.customer_id = %s")
        params.append(customer_id)
    if q:
        conds.append("(s.number ILIKE %s OR c.company_name ILIKE %s)")
        params += [f"%{q}%"] * 2
    where = "WHERE " + " AND ".join(conds) if conds else ""
    with connection() as conn:
        rows = conn.execute(
            f"""
            SELECT s.id, s.number, s.status, s.start_date, s.expiry_date, s.next_billing_date,
                   s.customer_id, c.company_name, p.name AS plan_name, p.billing_period,
                   (SELECT COALESCE(SUM(l.line_subtotal), 0) FROM subscription_lines l
                     WHERE l.subscription_id = s.id) AS recurring_amount,
                   COUNT(*) OVER() AS total_count
              FROM subscriptions s
              JOIN customers c ON c.id = s.customer_id
              JOIN plans p ON p.id = s.plan_id
              {where}
             ORDER BY s.id DESC LIMIT %s OFFSET %s
            """,
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
    return paged(rows, page, page_size)


def get_subscription(subscription_id: int, customer_id: int | None = None) -> dict:
    """Header, lines, history, discounts and the buttons the DB allows right now.

    Pass customer_id (from the login, never the URL) to scope it to one customer;
    someone else's subscription then looks exactly like a missing one (404).
    """
    with connection() as conn:
        sub = conn.execute(
            """
            SELECT s.*, c.company_name, p.name AS plan_name, p.billing_period,
                   pt.name AS payment_term
              FROM subscriptions s
              JOIN customers c ON c.id = s.customer_id
              JOIN plans p ON p.id = s.plan_id
              JOIN payment_terms pt ON pt.id = s.payment_term_id
             WHERE s.id = %s AND (%s::bigint IS NULL OR s.customer_id = %s)
            """,
            (subscription_id, customer_id, customer_id),
        ).fetchone()
        if not sub:
            raise not_found("Subscription")
        sub["lines"] = conn.execute(
            "SELECT id, description, quantity, unit_price, tax_name, tax_rate_bps, line_subtotal, line_tax "
            "FROM subscription_lines WHERE subscription_id = %s ORDER BY id",
            (subscription_id,),
        ).fetchall()
        sub["events"] = conn.execute(
            "SELECT e.from_status, e.to_status, e.changed_at, u.name AS changed_by_name "
            "FROM subscription_events e LEFT JOIN users u ON u.id = e.changed_by "
            "WHERE e.subscription_id = %s ORDER BY e.changed_at DESC, e.id DESC",
            (subscription_id,),
        ).fetchall()
        sub["discounts"] = conn.execute(
            "SELECT d.id, d.name, d.type, d.value FROM subscription_discounts sd "
            "JOIN discounts d ON d.id = sd.discount_id WHERE sd.subscription_id = %s",
            (subscription_id,),
        ).fetchall()
        sub["transitions"] = conn.execute(
            "SELECT to_status, action_label FROM status_transitions "
            "WHERE entity = 'SUBSCRIPTION' AND from_status = %s AND action_label IS NOT NULL "
            "ORDER BY action_label",
            (sub["status"],),
        ).fetchall()
    return sub


def transition_subscription(user_id: int, subscription_id: int, to_status: str) -> dict:
    """A status change is one UPDATE. The database decides if the move is legal.

    The two extra effects from the spec ride in the SAME statement:
      CONFIRMED -> ACTIVE : next_billing_date = start_date
      PAUSED    -> ACTIVE : next_billing_date = max(next_billing_date, today)
    (Every right-hand side in an UPDATE sees the OLD row, so `status` below is
    the status before the move.)
    """
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            """
            UPDATE subscriptions
               SET status = %(to)s::subscription_status_t,
                   next_billing_date = CASE
                       WHEN status = 'CONFIRMED' AND %(to)s = 'ACTIVE' THEN start_date
                       WHEN status = 'PAUSED'    AND %(to)s = 'ACTIVE'
                            THEN GREATEST(next_billing_date, (SELECT today FROM app_clock))
                       ELSE next_billing_date END,
                   updated_at = now()
             WHERE id = %(id)s
            RETURNING id, status
            """,
            {"to": to_status, "id": subscription_id},
        ).fetchone()
    if not row:
        raise not_found("Subscription")
    return row


def add_discount(user_id: int, subscription_id: int, discount_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        conn.execute(
            "INSERT INTO subscription_discounts (subscription_id, discount_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (subscription_id, discount_id),
        )
    return {"ok": True}


def remove_discount(user_id: int, subscription_id: int, discount_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        conn.execute(
            "DELETE FROM subscription_discounts WHERE subscription_id = %s AND discount_id = %s",
            (subscription_id, discount_id),
        )
    return {"ok": True}


def create_subscription(
    user_id: int,
    customer_id: int,
    plan_id: int,
    payment_term_id: int,
    start_date: date,
    expiry_date: date,
    lines: list[dict],
) -> dict:
    """Section 8.1: create a DRAFT subscription and snapshot every line's price and tax."""
    with transaction(user_id=user_id) as conn:
        plan = conn.execute(
            "SELECT id, name, price, min_quantity, available_from, available_to, tax_id, is_active "
            "FROM plans WHERE id = %s",
            (plan_id,),
        ).fetchone()
        if not plan or not plan["is_active"]:
            raise RuleError("Choose an active plan", 422, "plan_id")
        # The database does NOT check these two rules, so the service must.
        if start_date < plan["available_from"] or (
            plan["available_to"] and start_date > plan["available_to"]
        ):
            window = f"from {plan['available_from']}" + (
                f" to {plan['available_to']}" if plan["available_to"] else ""
            )
            raise RuleError(f"{plan['name']} is only available {window}", 422, "start_date")
        for ln in lines:
            if ln["quantity"] < plan["min_quantity"]:
                raise RuleError(
                    f"{plan['name']} needs a quantity of at least {plan['min_quantity']} per product",
                    422,
                    "lines",
                )

        sub = conn.execute(
            "INSERT INTO subscriptions (customer_id, plan_id, payment_term_id, start_date, "
            "expiry_date, created_by) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, number, status",
            (customer_id, plan_id, payment_term_id, start_date, expiry_date, user_id),
        ).fetchone()

        # Price and tax are copied (snapshotted) now, so later catalog edits
        # never rewrite an existing subscription.
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO subscription_lines (subscription_id, product_id, variant_id, description, "
                "quantity, unit_price, tax_name, tax_rate_bps) "
                "SELECT %s, p.id, v.id, p.name || COALESCE(' - ' || v.attribute || ': ' || v.value, ''), "
                "%s, p.sales_price + COALESCE(v.extra_price, 0), "
                "COALESCE(t.name, 'No tax'), COALESCE(t.rate_bps, 0) "
                "FROM products p LEFT JOIN taxes t ON t.id = p.tax_id "
                "LEFT JOIN product_variants v ON v.id = %s::bigint AND v.product_id = p.id "
                "WHERE p.id = %s",
                [(sub["id"], ln["quantity"], ln.get("variant_id"), ln["product_id"]) for ln in lines],
            )
        if plan["price"] > 0:  # plan fee line: product_id NULL, quantity 1
            conn.execute(
                "INSERT INTO subscription_lines (subscription_id, description, quantity, unit_price, "
                "tax_name, tax_rate_bps) SELECT %s, %s, 1, %s, COALESCE(t.name, 'No tax'), "
                "COALESCE(t.rate_bps, 0) FROM (SELECT 1) x LEFT JOIN taxes t ON t.id = %s",
                (sub["id"], f"{plan['name']} plan fee", plan["price"], plan["tax_id"]),
            )
    return sub
