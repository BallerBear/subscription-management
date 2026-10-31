"""Dashboard and report queries. All reports read from SQL views."""

from datetime import date

from app.core.db import connection


def get_kpis() -> dict:
    """Return the dashboard headline metrics. Money is in paise."""
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM v_dashboard_kpis"
        ).fetchone()

    if row is None:
        raise RuntimeError("Dashboard KPI view returned no row")

    return row


def monthly_collections(
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Return monthly collections, oldest first.

    Date filters include the entire calendar month containing each date.
    """
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("date_from cannot be after date_to")

    conditions = []
    params = []

    if date_from is not None:
        conditions.append("month >= date_trunc('month', %s::date)::date")
        params.append(date_from)

    if date_to is not None:
        conditions.append("month <= date_trunc('month', %s::date)::date")
        params.append(date_to)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    with connection() as conn:
        rows = conn.execute(
            f"""
            SELECT month, collected, payment_count
            FROM v_monthly_collections
            {where_clause}
            ORDER BY month ASC
            """,
            params,
        ).fetchall()

    return rows


def overdue_invoices(
    page: int = 1,
    page_size: int = 25,
    customer_id: int | None = None,
    plan_id: int | None = None,
) -> dict:
    """Return paginated overdue invoices, most overdue first."""
    if page < 1:
        raise ValueError("page must be at least 1")

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")

    conditions = []
    params = []

    if customer_id is not None:
        conditions.append("v.customer_id = %s")
        params.append(customer_id)

    if plan_id is not None:
        conditions.append("s.plan_id = %s")
        params.append(plan_id)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    offset = (page - 1) * page_size

    with connection() as conn:
        total = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM v_overdue_invoices v
            JOIN subscriptions s ON s.id = v.subscription_id
            {where_clause}
            """,
            params,
        ).fetchone()["total"]

        items = conn.execute(
            f"""
            SELECT v.*
            FROM v_overdue_invoices v
            JOIN subscriptions s ON s.id = v.subscription_id
            {where_clause}
            ORDER BY v.days_past_due DESC, v.due_date ASC, v.id ASC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        ).fetchall()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
