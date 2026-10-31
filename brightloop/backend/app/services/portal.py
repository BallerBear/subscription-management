"""Customer portal summary. Every query here is scoped by customer_id from the login."""

from app.core.db import connection


def portal_summary(customer_id: int) -> dict:
    with connection() as conn:
        due = conn.execute(
            "SELECT COALESCE(SUM(balance), 0) AS amount_due, MIN(due_date) AS next_due, "
            "COUNT(*) FILTER (WHERE is_overdue) AS overdue_count "
            "FROM v_invoice_summary WHERE customer_id = %s AND status = 'CONFIRMED' AND balance > 0",
            (customer_id,),
        ).fetchone()
        sub = conn.execute(
            "SELECT s.id, s.number, s.status, s.next_billing_date, p.name AS plan_name, "
            "p.billing_period FROM subscriptions s JOIN plans p ON p.id = s.plan_id "
            "WHERE s.customer_id = %s AND s.status IN ('ACTIVE', 'PAUSED') "
            "ORDER BY (s.status = 'ACTIVE') DESC, s.id DESC LIMIT 1",
            (customer_id,),
        ).fetchone()
    return {**due, "subscription": sub}
