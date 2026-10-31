"""Recording payments.

Not implemented yet. Triggers do the heavy lifting (balance check, amount_paid, flip to PAID);
this service only checks what the database cannot: paid_on is not after 'today'.
"""

from datetime import date


def record_payment(
    user_id: int,
    invoice_id: int,
    method: str,
    amount: int,
    paid_on: date,
    reference: str | None = None,
    note: str | None = None,
) -> dict:
    """Insert one payment (amount in paise). Returns the new payment row as a dict.

    Raises ValueError if paid_on is after app_clock.today. Overpayment or a
    non-CONFIRMED invoice raises a readable database error (P0001).
    """
    raise NotImplementedError


def list_payments(
    page: int = 1,
    page_size: int = 25,
    invoice_id: int | None = None,
    customer_id: int | None = None,
) -> dict:
    """Paginated payments with invoice number and company name, one JOIN.

    Returns {"items": [...], "total": int, "page": int, "page_size": int}.
    """
    raise NotImplementedError
