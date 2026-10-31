"""Recording and listing invoice payments.

The database triggers enforce invoice status, outstanding balance,
invoice amount_paid updates, and the automatic PAID transition.
"""

from datetime import date

from app.core.db import connection, transaction


PAYMENT_METHODS = {
    "CARD",
    "UPI",
    "BANK_TRANSFER",
    "CASH",
    "CHEQUE",
}


def record_payment(
    user_id: int,
    invoice_id: int,
    method: str,
    amount: int,
    paid_on: date,
    reference: str | None = None,
    note: str | None = None,
) -> dict:
    """Insert one payment (amount in paise).

    Raises ValueError for invalid input or a payment dated after app_clock.today.
    Database trigger errors are allowed to propagate.
    """
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero")

    if method not in PAYMENT_METHODS:
        raise ValueError(
            f"Invalid payment method: {method}. "
            f"Choose one of: {', '.join(sorted(PAYMENT_METHODS))}"
        )

    with transaction(user_id=user_id) as conn:
        today = conn.execute(
            "SELECT today FROM app_clock WHERE singleton = TRUE"
        ).fetchone()["today"]

        if paid_on > today:
            raise ValueError(
                f"Payment date {paid_on} cannot be after today ({today})"
            )

        row = conn.execute(
            """
            INSERT INTO payments (
                invoice_id,
                method,
                amount,
                paid_on,
                reference,
                note,
                recorded_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                invoice_id,
                method,
                amount,
                paid_on,
                reference,
                note,
                recorded_by,
                created_at
            """,
            (
                invoice_id,
                method,
                amount,
                paid_on,
                reference,
                note,
                user_id,
            ),
        ).fetchone()

    return row


def list_payments(
    page: int = 1,
    page_size: int = 25,
    invoice_id: int | None = None,
    customer_id: int | None = None,
) -> dict:
    """Return paginated payments with invoice number and company name."""
    if page < 1:
        raise ValueError("page must be at least 1")

    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")

    conditions = []
    params = []

    if invoice_id is not None:
        conditions.append("p.invoice_id = %s")
        params.append(invoice_id)

    if customer_id is not None:
        conditions.append("i.customer_id = %s")
        params.append(customer_id)

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
            FROM payments p
            JOIN invoices i ON i.id = p.invoice_id
            {where_clause}
            """,
            params,
        ).fetchone()["total"]

        items = conn.execute(
            f"""
            SELECT
                p.id,
                p.invoice_id,
                p.method,
                p.amount,
                p.paid_on,
                p.reference,
                p.note,
                p.recorded_by,
                p.created_at,
                i.number AS invoice_number,
                c.company_name
            FROM payments p
            JOIN invoices i ON i.id = p.invoice_id
            JOIN customers c ON c.id = i.customer_id
            {where_clause}
            ORDER BY p.paid_on DESC, p.id DESC
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
