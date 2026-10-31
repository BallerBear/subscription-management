"""Discount application at billing time (CLAUDE.md section 8.4).

STUB. Discount CRUD (admin screens) belongs to Person 3; this module is only
the part the billing engine calls.
"""

import psycopg


def apply_discounts(conn: psycopg.Connection, new_invoice_ids: list[int]) -> int:
    """Apply eligible discounts to freshly created DRAFT invoices.

    Runs inside the billing transaction (uses the caller's conn). Updates
    invoice_lines.discount_amount and inserts discount_redemptions; the
    redemption trigger bumps times_used. Uses executemany, never a query loop.

    Returns the number of redemptions written.
    """
    raise NotImplementedError
