"""Apply eligible subscription discounts to newly created draft invoices."""

import psycopg


def _allocate_discount(lines: list[dict], amount: int, total: int) -> None:
    """Distribute a discount proportionally across eligible invoice lines."""
    if amount <= 0 or total <= 0:
        return

    amount = min(amount, total)
    allocations = []

    for line in lines:
        remaining = line["line_subtotal"] - line["discount_amount"]
        share = (amount * remaining) // total
        allocations.append(share)

    # Distribute rounding remainder deterministically.
    remainder = amount - sum(allocations)

    for index, line in enumerate(lines):
        if remainder <= 0:
            break

        available = (
            line["line_subtotal"]
            - line["discount_amount"]
            - allocations[index]
        )
        extra = min(available, remainder)
        allocations[index] += extra
        remainder -= extra

    # Apply every calculated allocation, including lines after the remainder
    # has been exhausted.
    for line, share in zip(lines, allocations):
        line["discount_amount"] += share


def apply_discounts(
    conn: psycopg.Connection,
    new_invoice_ids: list[int],
) -> int:
    """Apply eligible discounts to freshly created DRAFT invoices.

    Must run inside the caller's billing transaction.
    Returns the number of discount redemptions inserted.
    """
    if not new_invoice_ids:
        return 0

    today = conn.execute(
        "SELECT today FROM app_clock WHERE singleton = TRUE"
    ).fetchone()["today"]

    # Lock discount rows in a consistent order. This protects usage limits
    # when simultaneous billing runs share the same discounts.
    candidates = conn.execute(
        """
        SELECT
            i.id AS invoice_id,
            i.subscription_id,
            d.id AS discount_id,
            d.type,
            d.value,
            d.scope,
            d.product_id,
            d.min_purchase,
            d.min_quantity,
            d.usage_limit,
            d.times_used
        FROM invoices AS i
        JOIN subscription_discounts AS sd
          ON sd.subscription_id = i.subscription_id
        JOIN discounts AS d
          ON d.id = sd.discount_id
        WHERE i.id = ANY(%s)
          AND d.is_active = TRUE
          AND d.start_date <= %s
          AND (d.end_date IS NULL OR d.end_date >= %s)
        ORDER BY d.id, i.id
        FOR UPDATE OF d
        """,
        (new_invoice_ids, today, today),
    ).fetchall()

    if not candidates:
        return 0

    line_rows = conn.execute(
        """
        SELECT
            id,
            invoice_id,
            product_id,
            quantity,
            line_subtotal,
            discount_amount
        FROM invoice_lines
        WHERE invoice_id = ANY(%s)
        ORDER BY invoice_id, id
        """,
        (new_invoice_ids,),
    ).fetchall()

    lines_by_invoice: dict[int, list[dict]] = {}
    for row in line_rows:
        line = dict(row)
        lines_by_invoice.setdefault(line["invoice_id"], []).append(line)

    # Track usage locally too: the database trigger increments times_used
    # only after redemption inserts, so repeated candidates in this batch
    # must account for earlier redemptions.
    usage_counts: dict[int, int] = {}
    line_updates = []
    redemptions = []

    for discount in candidates:
        discount_id = discount["discount_id"]

        if discount_id not in usage_counts:
            usage_counts[discount_id] = discount["times_used"]

        used = usage_counts[discount_id]
        limit = discount["usage_limit"]

        if limit is not None and used >= limit:
            continue

        invoice_lines = lines_by_invoice.get(discount["invoice_id"], [])

        if discount["scope"] == "PRODUCT":
            eligible = [
                line for line in invoice_lines
                if line["product_id"] == discount["product_id"]
            ]
        else:
            eligible = invoice_lines

        # Only the remaining undiscounted value can receive another discount.
        eligible = [
            line for line in eligible
            if line["line_subtotal"] > line["discount_amount"]
        ]

        if not eligible:
            continue

        eligible_total = sum(
            line["line_subtotal"] - line["discount_amount"]
            for line in eligible
        )
        eligible_quantity = sum(line["quantity"] for line in eligible)

        if eligible_total < discount["min_purchase"]:
            continue

        if eligible_quantity < discount["min_quantity"]:
            continue

        if discount["type"] == "FIXED":
            amount = min(discount["value"], eligible_total)
        else:
            # Half-up rounding, in whole paise.
            amount = (
                eligible_total * discount["value"] + 5000
            ) // 10000
            amount = min(amount, eligible_total)

        if amount <= 0:
            continue

        _allocate_discount(eligible, amount, eligible_total)

        redemptions.append(
            (discount_id, discount["invoice_id"], amount)
        )
        usage_counts[discount_id] += 1

    if not redemptions:
        return 0

    # Write each changed invoice line once, after all discounts have been
    # allocated. PostgreSQL recalculates invoice totals via its trigger.
    changed_lines = [
        line
        for invoice_lines in lines_by_invoice.values()
        for line in invoice_lines
        if line["discount_amount"] > 0
    ]

    # executemany lives on the cursor, not the connection (psycopg 3).
    with conn.cursor() as cur:
        if changed_lines:
            cur.executemany(
                """
                UPDATE invoice_lines
                   SET discount_amount = %s
                 WHERE id = %s
                """,
                [
                    (line["discount_amount"], line["id"])
                    for line in changed_lines
                ],
            )

        cur.executemany(
            """
            INSERT INTO discount_redemptions (
                discount_id,
                invoice_id,
                amount
            )
            VALUES (%s, %s, %s)
            """,
            redemptions,
        )

    return len(redemptions)
