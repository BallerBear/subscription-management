"""Billing engine: turns due ACTIVE subscriptions into invoices."""

from calendar import monthrange
from datetime import date, timedelta

from app.core.db import transaction
from app.services.discounts import apply_discounts


def _add_months(value: date, months: int, anchor_day: int) -> date:
    """Advance calendar months while preserving the original billing day."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1

    last_day = monthrange(year, month)[1]
    return date(year, month, min(anchor_day, last_day))


def _next_period(
    value: date,
    billing_period: str,
    anchor_date: date,
) -> date:
    """Return the next period start, preserving the subscription's anchor."""
    if billing_period == "DAILY":
        return value + timedelta(days=1)

    if billing_period == "WEEKLY":
        return value + timedelta(days=7)

    if billing_period == "MONTHLY":
        return _add_months(value, 1, anchor_date.day)

    if billing_period == "YEARLY":
        return _add_months(value, 12, anchor_date.day)

    raise ValueError(f"Unsupported billing period: {billing_period}")


def run_billing(user_id: int, auto_confirm: bool = True) -> dict:
    """Bill all due active subscriptions as of app_clock.today.

    Creates one invoice per subscription and billing period.
    Safe to rerun: the database unique constraint prevents duplicates.
    """

    with transaction(user_id=user_id) as conn:
        today = conn.execute(
            "SELECT today FROM app_clock WHERE singleton = TRUE"
        ).fetchone()["today"]

        # Close expired subscriptions whose plans require automatic closure.
        closed_rows = conn.execute(
            """
            UPDATE subscriptions AS s
               SET status = 'CLOSED'
              FROM plans AS p
             WHERE p.id = s.plan_id
               AND s.status = 'ACTIVE'
               AND p.auto_close = TRUE
               AND s.expiry_date <= %s
            RETURNING s.id
            """,
            (today,),
        ).fetchall()
        closed = len(closed_rows)

        # Lock due subscriptions so concurrent billing runs cannot process
        # the same subscription simultaneously.
        subscriptions = conn.execute(
            """
            SELECT
                s.id,
                s.customer_id,
                s.start_date,
                s.next_billing_date,
                s.expiry_date,
                p.billing_period,
                pt.days AS payment_days
            FROM subscriptions AS s
            JOIN plans AS p ON p.id = s.plan_id
            JOIN payment_terms AS pt ON pt.id = s.payment_term_id
            WHERE s.status = 'ACTIVE'
              AND s.next_billing_date <= %s
              AND s.expiry_date > %s
            ORDER BY s.id
            FOR UPDATE OF s
            """,
            (today, today),
        ).fetchall()

        # Build all invoice periods in memory. No database query is performed
        # inside this loop.
        invoice_values = []
        next_dates = []

        for sub in subscriptions:
            current = sub["next_billing_date"]

            while current <= today and current < sub["expiry_date"]:
                period_end = _next_period(
                    current,
                    sub["billing_period"],
                    sub["start_date"],
                )

                invoice_values.append(
                    (
                        sub["id"],
                        sub["customer_id"],
                        current,
                        period_end,
                        today,
                        today + timedelta(days=sub["payment_days"]),
                    )
                )

                current = period_end

            # Advance even if an invoice already exists for one of these
            # periods. This prevents a conflicting invoice from blocking
            # future billing runs.
            if current != sub["next_billing_date"]:
                next_dates.append((current, sub["id"]))

        created_invoice_ids = []
        skipped = 0

        # Insert in batches to stay below PostgreSQL's 65,535 parameter limit.
        batch_size = 5000

        for start in range(0, len(invoice_values), batch_size):
            batch = invoice_values[start:start + batch_size]

            row_placeholder = "(%s, %s, %s, %s, %s, %s)"
            placeholders = ", ".join(row_placeholder for _ in batch)
            params = [
                value
                for invoice in batch
                for value in invoice
            ]

            inserted = conn.execute(
                f"""
                INSERT INTO invoices (
                    subscription_id,
                    customer_id,
                    period_start,
                    period_end,
                    issue_date,
                    due_date
                )
                VALUES {placeholders}
                ON CONFLICT (subscription_id, period_start) DO NOTHING
                RETURNING id
                """,
                params,
            ).fetchall()

            created_invoice_ids.extend(row["id"] for row in inserted)
            skipped += len(batch) - len(inserted)

        # Copy the recurring plan fee and snapshotted subscription lines.
        # PostgreSQL triggers calculate invoice totals automatically.
        if created_invoice_ids:
            conn.execute(
                """
                INSERT INTO invoice_lines (
                    invoice_id,
                    product_id,
                    description,
                    quantity,
                    unit_price,
                    discount_amount,
                    tax_name,
                    tax_rate_bps
                )
                SELECT
                    i.id,
                    NULL,
                    'Plan fee - ' || p.name,
                    1,
                    p.price,
                    0,
                    t.name,
                    t.rate_bps
                FROM invoices AS i
                JOIN subscriptions AS s ON s.id = i.subscription_id
                JOIN plans AS p ON p.id = s.plan_id
                JOIN taxes AS t ON t.id = p.tax_id
                WHERE i.id = ANY(%s)
                  AND p.price > 0

                UNION ALL

                SELECT
                    i.id,
                    sl.product_id,
                    sl.description,
                    sl.quantity,
                    sl.unit_price,
                    0,
                    sl.tax_name,
                    sl.tax_rate_bps
                FROM invoices AS i
                JOIN subscription_lines AS sl
                  ON sl.subscription_id = i.subscription_id
                WHERE i.id = ANY(%s)
                """,
                (created_invoice_ids, created_invoice_ids),
            )

            # Discounts must be applied while invoices are still DRAFT.
            apply_discounts(conn, created_invoice_ids)

            if auto_confirm:
                conn.execute(
                    """
                    UPDATE invoices
                       SET status = 'CONFIRMED'
                     WHERE id = ANY(%s)
                       AND status = 'DRAFT'
                    """,
                    (created_invoice_ids,),
                )

        # Advance every processed subscription, including those whose
        # invoice periods were skipped because of the unique constraint.
        if next_dates:
            conn.executemany(
                """
                UPDATE subscriptions
                   SET next_billing_date = %s
                 WHERE id = %s
                """,
                next_dates,
            )

        up_to_date = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM subscriptions
            WHERE status = 'ACTIVE'
              AND next_billing_date > %s
              AND expiry_date > %s
            """,
            (today, today),
        ).fetchone()["count"]

    return {
        "created": len(created_invoice_ids),
        "skipped": skipped,
        "closed": closed,
        "up_to_date": up_to_date,
        "as_of": today,
    }


def confirm_all_drafts(user_id: int) -> dict:
    """Confirm all DRAFT invoices in one transaction."""
    with transaction(user_id=user_id) as conn:
        rows = conn.execute(
            """
            UPDATE invoices
               SET status = 'CONFIRMED'
             WHERE status = 'DRAFT'
            RETURNING id
            """
        ).fetchall()

    return {"confirmed": len(rows)}
