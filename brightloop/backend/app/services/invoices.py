"""Invoices: lists and detail read the v_invoice_summary view; moves are plain UPDATEs.

No totals are computed here. Generated columns and triggers own all the math.
"""

from datetime import date

from app.core.db import connection, transaction
from app.services.common import RuleError, not_found, paged

_LIST_COLS = (
    "v.id, v.number, v.subscription_id, v.customer_id, v.company_name, v.status, "
    "v.period_start, v.period_end, v.issue_date, v.due_date, v.total, v.amount_paid, "
    "v.balance, v.is_overdue, v.days_past_due, v.sent_at"
)


def list_invoices(
    status: str | None = None,
    customer_id: int | None = None,
    overdue: bool = False,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 25,
    hide_drafts: bool = False,
) -> dict:
    conds, params = [], []
    if hide_drafts:  # the customer portal never shows internal drafts
        conds.append("v.status <> 'DRAFT'")
    if status:
        conds.append("v.status = %s::invoice_status_t")
        params.append(status)
    if customer_id:
        conds.append("v.customer_id = %s")
        params.append(customer_id)
    if overdue:
        conds.append("v.is_overdue")
    if q:
        conds.append("(v.number ILIKE %s OR v.company_name ILIKE %s)")
        params += [f"%{q}%"] * 2
    if date_from:
        conds.append("v.issue_date >= %s")
        params.append(date_from)
    if date_to:
        conds.append("v.issue_date <= %s")
        params.append(date_to)
    where = "WHERE " + " AND ".join(conds) if conds else ""
    with connection() as conn:
        rows = conn.execute(
            f"SELECT {_LIST_COLS}, COUNT(*) OVER() AS total_count FROM v_invoice_summary v "
            f"{where} ORDER BY v.issue_date DESC, v.id DESC LIMIT %s OFFSET %s",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
    return paged(rows, page, page_size)


def get_invoice(invoice_id: int, customer_id: int | None = None) -> dict:
    """Full invoice for the detail/print page. customer_id scopes it to one customer."""
    with connection() as conn:
        inv = conn.execute(
            f"""
            SELECT {_LIST_COLS}, v.subtotal, v.discount_total, v.tax_total,
                   c.contact_name, c.email, c.phone, c.address_line, c.city, c.state,
                   c.postal_code, c.country, c.gstin, s.number AS subscription_number
              FROM v_invoice_summary v
              JOIN customers c ON c.id = v.customer_id
              JOIN subscriptions s ON s.id = v.subscription_id
             WHERE v.id = %s AND (%s::bigint IS NULL OR (v.customer_id = %s AND v.status <> 'DRAFT'))
            """,
            (invoice_id, customer_id, customer_id),
        ).fetchone()
        if not inv:
            raise not_found("Invoice")
        inv["lines"] = conn.execute(
            "SELECT id, description, quantity, unit_price, discount_amount, tax_name, tax_rate_bps, "
            "line_subtotal, tax_amount, line_total FROM invoice_lines WHERE invoice_id = %s ORDER BY id",
            (invoice_id,),
        ).fetchall()
        inv["payments"] = conn.execute(
            "SELECT id, method, amount, paid_on, reference, note FROM payments "
            "WHERE invoice_id = %s ORDER BY paid_on, id",
            (invoice_id,),
        ).fetchall()
        inv["transitions"] = conn.execute(
            "SELECT to_status, action_label FROM status_transitions "
            "WHERE entity = 'INVOICE' AND from_status = %s AND action_label IS NOT NULL "
            "ORDER BY action_label",
            (inv["status"],),
        ).fetchall()
    return inv


def transition_invoice(user_id: int, invoice_id: int, to_status: str) -> dict:
    """Confirm / cancel: one UPDATE; the database rejects illegal moves."""
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            "UPDATE invoices SET status = %s::invoice_status_t WHERE id = %s RETURNING id, status",
            (to_status, invoice_id),
        ).fetchone()
    if not row:
        raise not_found("Invoice")
    return row


def send_invoice(user_id: int, invoice_id: int) -> dict:
    with transaction(user_id=user_id) as conn:
        row = conn.execute(
            "UPDATE invoices SET sent_at = now() WHERE id = %s AND status IN ('CONFIRMED', 'PAID') "
            "RETURNING id, sent_at",
            (invoice_id,),
        ).fetchone()
        if not row:
            exists = conn.execute("SELECT 1 FROM invoices WHERE id = %s", (invoice_id,)).fetchone()
            if not exists:
                raise not_found("Invoice")
            raise RuleError("Confirm the invoice before sending it", 409)
    return row
