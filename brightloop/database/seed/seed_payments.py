"""Add believable payments to the already-seeded invoices (demo data).

Run once from backend/:   python ../database/seed/seed_payments.py

What it creates (one set-based INSERT, no loop, so it is one round trip):
  * ~65% of confirmed invoices paid in full
  * ~10% partly paid (40%)
  * the rest unpaid, which leaves a realistic tail of overdue invoices
Methods rotate through CARD / UPI / BANK_TRANSFER / CASH / CHEQUE.

The payment triggers still run, so amount_paid and the PAID status are set by
the database, exactly as for a payment recorded in the UI.
It refuses to run twice (it exits if any payment already exists).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.db import connection, transaction  # noqa: E402


def main() -> None:
    with connection() as conn:
        if conn.execute("SELECT count(*) AS n FROM payments").fetchone()["n"]:
            print("Payments already exist. Nothing changed.")
            return
        staff = conn.execute("SELECT id FROM users WHERE role = 'STAFF' ORDER BY id LIMIT 1").fetchone()

    with transaction(user_id=staff["id"]) as conn:
        rows = conn.execute(
            """
            INSERT INTO payments (invoice_id, method, amount, paid_on, reference, recorded_by)
            SELECT i.id,
                   (ARRAY['CARD','UPI','BANK_TRANSFER','CASH','CHEQUE'])[1 + i.id %% 5]::payment_method_t,
                   CASE WHEN i.id %% 20 < 13 THEN i.total              -- most are paid in full
                        ELSE (i.total * 4 / 10) END,                  -- some are part-paid
                   -- paid a little before/after the due date, never in the future or before issue
                   GREATEST(i.issue_date, LEAST(k.today, i.due_date - 3 + (i.id %% 7)::int)),
                   'REF-' || lpad(i.id::text, 6, '0'),
                   %s
              FROM invoices i CROSS JOIN app_clock k
             WHERE i.status = 'CONFIRMED' AND i.id %% 20 < 15          -- the rest stay unpaid
            RETURNING 1
            """,
            (staff["id"],),
        ).fetchall()
    print(f"Recorded {len(rows)} payments.")


if __name__ == "__main__":
    main()
