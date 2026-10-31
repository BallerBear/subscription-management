"""Seed demo data: logins, catalog, customers and ACTIVE subscriptions.

Run from the repo root:   backend/.venv/bin/python database/seed/seed.py

What it does NOT do (yet): create invoices or payments. Those come from the
real billing engine, so the numbers stay internally consistent. After the
engine exists, click "Run billing" in the Time Machine and watch it catch up.

Safe to re-run: if subscriptions already exist it exits without touching
anything. It never DROPs, TRUNCATEs or DELETEs.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Make `import app...` work when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.db import connection, transaction  # noqa: E402
from app.core.security import hash_password  # noqa: E402

DEMO_PASSWORD = "Brightloop@123"  # meets the rules: 9+ chars, upper, lower, special

# (company, contact, city, state, GST state code). Hand-written on purpose.
CUSTOMERS = [
    ("Kaveri Textiles Pvt Ltd", "Meenakshi Iyer", "Coimbatore", "Tamil Nadu", "33"),
    ("Sahyadri Foods", "Rohan Kulkarni", "Pune", "Maharashtra", "27"),
    ("Lotus Dental Care", "Dr. Anjali Verma", "Lucknow", "Uttar Pradesh", "09"),
    ("Marina Logistics", "Karthik Raman", "Chennai", "Tamil Nadu", "33"),
    ("Bluewave Exports", "Farhan Sheikh", "Mumbai", "Maharashtra", "27"),
    ("Nandi Agro Tech", "Suresh Gowda", "Bengaluru", "Karnataka", "29"),
    ("Pinnacle Coaching Centre", "Deepa Nair", "Kochi", "Kerala", "32"),
    ("Rajputana Handicrafts", "Vikram Singh Rathore", "Jaipur", "Rajasthan", "08"),
    ("Greenfield Realty", "Harpreet Kaur", "Ludhiana", "Punjab", "03"),
    ("Orchid Wellness Spa", "Priyanka Das", "Kolkata", "West Bengal", "19"),
    ("Tiruppur Knit Works", "Senthil Kumar", "Tiruppur", "Tamil Nadu", "33"),
    ("Anand Auto Components", "Jignesh Patel", "Rajkot", "Gujarat", "24"),
    ("Charminar Catering", "Imran Qureshi", "Hyderabad", "Telangana", "36"),
    ("Himalayan Tea Traders", "Tenzin Bhutia", "Siliguri", "West Bengal", "19"),
    ("Delta Pharma Distributors", "Rakesh Mehta", "Ahmedabad", "Gujarat", "24"),
    ("Konkan Fisheries Co-op", "Savita Naik", "Panaji", "Goa", "30"),
    ("Vidya Mandir Publications", "Arvind Choudhary", "Patna", "Bihar", "10"),
    ("Silverline Cinemas", "Nisha Menon", "Thiruvananthapuram", "Kerala", "32"),
    ("Malwa Seeds & Fertilisers", "Gurpreet Sandhu", "Indore", "Madhya Pradesh", "23"),
    ("Urban Nest Interiors", "Aditi Bhatt", "Surat", "Gujarat", "24"),
]


def gstin(i: int, state_code: str) -> str:
    """Valid-format GSTIN: 2 digits + 5 letters + 4 digits + letter + 1 + Z + 5."""
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    pan = letters[i % 24] + letters[(i * 3) % 24] + "CPK"  # exactly 5 letters
    return f"{state_code}{pan}{1000 + i * 37:04d}{letters[(i * 5) % 24]}1Z5"


def seed_users() -> dict:
    """Admin, staff and a customer login. Returns {role: user_id}."""
    pw = hash_password(DEMO_PASSWORD)
    rows = [
        ("admin@brightloop.example.com", pw, "Asha Admin", "ADMIN"),
        ("staff@brightloop.example.com", pw, "Sam Staff", "STAFF"),
        ("customer@kaveri.example.com", pw, "Meenakshi Iyer", "CUSTOMER"),
    ]
    with transaction() as conn:
        with conn.cursor() as cur:
            # One round trip for all three; re-runs skip rows that exist.
            cur.executemany(
                "INSERT INTO users (email, password_hash, name, role) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                rows,
            )
        found = conn.execute(
            "SELECT id, role, email FROM users WHERE email = ANY(%s)",
            ([r[0] for r in rows],),
        ).fetchall()
    return {r["role"]: r["id"] for r in found}


def seed_catalog(conn) -> None:
    """Taxes, products (+variants) and plans. Names are looked up, not hard-coded ids."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO taxes (name, rate_bps) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
            [("GST 18%", 1800), ("GST 5%", 500), ("GST 0%", 0)],
        )
        # Prices are integer paise: 2499.00 rupees = 249900.
        cur.executemany(
            "INSERT INTO products (name, type, sales_price, cost_price, tax_id) "
            "SELECT %s, %s::product_type_t, %s, %s, id FROM taxes WHERE name = 'GST 18%%'",
            [
                ("Business Suite (per seat)", "SOFTWARE", 249900, 90000),
                ("Analytics Add-on", "ADD_ON", 79900, 21000),
                ("Priority Support", "SERVICE", 149900, 60000),
                ("Onboarding Package", "SERVICE", 999900, 450000),
            ],
        )
        cur.executemany(
            "INSERT INTO product_variants (product_id, attribute, value, extra_price) "
            "SELECT id, 'Edition', %s, %s FROM products WHERE name = 'Business Suite (per seat)'",
            [("Standard", 0), ("Pro", 50000)],
        )
        # (name, fee, period, min_qty, auto_close, allow_pause)
        cur.executemany(
            "INSERT INTO plans (name, price, billing_period, min_quantity, available_from, "
            "tax_id, auto_close, allow_pause) "
            "SELECT %s, %s, %s::billing_period_t, %s, DATE '2026-01-01', id, %s, %s "
            "FROM taxes WHERE name = 'GST 18%%'",
            [
                ("Starter Monthly", 0, "MONTHLY", 1, False, False),
                ("Team Monthly", 99900, "MONTHLY", 3, False, True),
                ("Business Yearly", 999900, "YEARLY", 5, False, True),
                ("Weekly Trial", 0, "WEEKLY", 1, True, False),
            ],
        )


def seed_customers_and_subs(conn, ids: dict, today: date) -> int:
    """~20 customers, one ACTIVE subscription each, started over the last ~6 months."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO customers (user_id, company_name, contact_name, email, phone, "
            "city, state, postal_code, gstin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    ids["CUSTOMER"] if i == 0 else None,  # the demo customer owns Kaveri
                    company,
                    contact,
                    f"accounts{i + 1}@example.com",
                    f"+91 98{40000000 + i * 137731:08d}",
                    city,
                    state,
                    f"{600001 + i * 1031:06d}",
                    gstin(i, code),
                )
                for i, (company, contact, city, state, code) in enumerate(CUSTOMERS)
            ],
        )

    plans = {
        r["name"]: r
        for r in conn.execute(
            "SELECT id, name, billing_period, min_quantity FROM plans"
        ).fetchall()
    }
    terms = [r["id"] for r in conn.execute("SELECT id FROM payment_terms ORDER BY days").fetchall()]
    customers = conn.execute("SELECT id FROM customers ORDER BY id").fetchall()
    mix = ["Starter Monthly", "Team Monthly", "Business Yearly", "Team Monthly", "Starter Monthly"]

    sub_rows = []
    for i, cust in enumerate(customers):
        plan = plans["Weekly Trial"] if i == 7 else plans[mix[i % len(mix)]]
        # Start days 1-28 (avoids month-end drift); spread over May-Oct 2026.
        start = date(2026, 5 + (i % 6), 1 + (i * 5) % 28)
        if plan["name"] == "Weekly Trial":
            start, expiry = today - timedelta(days=20), today + timedelta(days=9)  # expires soon
        else:
            expiry = date(start.year + 1, start.month, start.day)
        sub_rows.append((cust["id"], plan["id"], terms[i % len(terms)], start, expiry, ids["ADMIN"]))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO subscriptions (customer_id, plan_id, payment_term_id, start_date, "
            "expiry_date, created_by) VALUES (%s, %s, %s, %s, %s, %s)",
            sub_rows,
        )
    subs = conn.execute(
        "SELECT s.id, s.plan_id, p.name AS plan_name, p.min_quantity FROM subscriptions s "
        "JOIN plans p ON p.id = s.plan_id ORDER BY s.id"
    ).fetchall()

    # Product lines: snapshot price and tax from the catalog, exactly like section 8.1.
    products = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM products").fetchall()}
    pro = conn.execute("SELECT id FROM product_variants WHERE value = 'Pro'").fetchone()["id"]
    suite, analytics, support = (
        products["Business Suite (per seat)"],
        products["Analytics Add-on"],
        products["Priority Support"],
    )
    line_rows = []
    for i, s in enumerate(subs):
        qty = s["min_quantity"] + i % 4  # uneven quantities, always >= plan minimum
        line_rows.append((s["id"], suite, pro if i % 3 == 0 else None, qty))
        if i % 2 == 0:
            line_rows.append((s["id"], analytics, None, 1))
        if i % 5 == 0:
            line_rows.append((s["id"], support, None, 1))
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO subscription_lines (subscription_id, product_id, variant_id, "
            "description, quantity, unit_price, tax_name, tax_rate_bps) "
            "SELECT %s, p.id, v.id, p.name || COALESCE(' - ' || v.attribute || ': ' || v.value, ''), "
            "%s, p.sales_price + COALESCE(v.extra_price, 0), t.name, t.rate_bps "
            "FROM products p JOIN taxes t ON t.id = p.tax_id "
            "LEFT JOIN product_variants v ON v.id = %s::bigint "
            "WHERE p.id = %s",
            [(sid, qty, vid, pid) for sid, pid, vid, qty in line_rows],
        )
    # Plan fee line for every plan that has a fee: one set-based INSERT, no loop.
    conn.execute(
        "INSERT INTO subscription_lines (subscription_id, description, quantity, unit_price, "
        "tax_name, tax_rate_bps) "
        "SELECT s.id, p.name || ' plan fee', 1, p.price, t.name, t.rate_bps "
        "FROM subscriptions s JOIN plans p ON p.id = s.plan_id JOIN taxes t ON t.id = p.tax_id "
        "WHERE p.price > 0"
    )

    # Walk the lifecycle with plain UPDATEs; the database checks every hop.
    all_ids = [s["id"] for s in subs]
    conn.execute("UPDATE subscriptions SET status = 'QUOTATION' WHERE id = ANY(%s)", (all_ids,))
    conn.execute("UPDATE subscriptions SET status = 'CONFIRMED' WHERE id = ANY(%s)", (all_ids,))
    conn.execute(
        "UPDATE subscriptions SET status = 'ACTIVE', next_billing_date = start_date "
        "WHERE id = ANY(%s)",
        (all_ids,),
    )
    # A believable mix: two paused (only plans that allow it), one closed.
    pausable = [s["id"] for s in subs if s["plan_name"] in ("Team Monthly", "Business Yearly")][:2]
    conn.execute("UPDATE subscriptions SET status = 'PAUSED' WHERE id = ANY(%s)", (pausable,))
    conn.execute("UPDATE subscriptions SET status = 'CLOSED' WHERE id = %s", (subs[-1]["id"],))
    return len(subs)


def main() -> None:
    with connection() as conn:
        already = conn.execute("SELECT count(*) AS n FROM subscriptions").fetchone()["n"]
        today = conn.execute("SELECT today FROM app_clock").fetchone()["today"]
    if already:
        print(f"Already seeded ({already} subscriptions). Nothing changed.")
        return

    ids = seed_users()
    # user_id is stored in the transaction so history/audit rows say who acted.
    with transaction(user_id=ids["ADMIN"]) as conn:
        seed_catalog(conn)
        n = seed_customers_and_subs(conn, ids, today)

    print(f"Seeded {n} subscriptions as of app_clock.today = {today}.")
    print(f"Demo logins (password for all: {DEMO_PASSWORD}):")
    print("  admin    admin@brightloop.example.com")
    print("  staff    staff@brightloop.example.com")
    print("  customer customer@kaveri.example.com")


if __name__ == "__main__":
    main()
