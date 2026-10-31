"""Dashboard and report queries. All read from the SQL views (CLAUDE.md section 7).

STUB: shapes are final so the dashboard can be built against them.
"""

from datetime import date


def get_kpis() -> dict:
    """One row from v_dashboard_kpis: {"active_subscriptions", "mrr",
    "collected_this_month", "outstanding", "overdue_invoices",
    "overdue_amount", "as_of"}. Money in paise."""
    raise NotImplementedError


def monthly_collections(date_from: date | None = None, date_to: date | None = None) -> list[dict]:
    """Rows of {"month": date, "collected": int, "payment_count": int}
    from v_monthly_collections, oldest first."""
    raise NotImplementedError


def overdue_invoices(
    page: int = 1,
    page_size: int = 25,
    customer_id: int | None = None,
    plan_id: int | None = None,
) -> dict:
    """Paginated rows from v_overdue_invoices, worst first (days_past_due DESC).

    Returns {"items": [...], "total": int, "page": int, "page_size": int}.
    """
    raise NotImplementedError
