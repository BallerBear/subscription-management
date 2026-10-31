"""Measure the dashboard/portal queries WITH and WITHOUT indexes and write results.md.

    python database/explain/run_explain.py            # build data, measure, keep the data
    python database/explain/run_explain.py --cleanup  # also DROP SCHEMA perf_demo at the end

Needs only DATABASE_URL (from .env). It touches nothing outside the perf_demo schema.
"""

import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[1] / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://brightloop:brightloop_local@localhost:5432/brightloop")

# The secondary indexes we drop for the "without" run. Primary keys and UNIQUE
# constraints stay: they protect data integrity, they are not performance extras.
SECONDARY_INDEXES = [
    "idx_customers_company_trgm",
    "idx_subscriptions_due",
    "idx_invoices_customer",
    "idx_invoices_status",
    "idx_invoices_open",
    "idx_invoices_issue_date",
    "idx_payments_invoice",
    "idx_payments_paid_on",
]
SCAN_RE = re.compile(r"(Seq Scan|Index Only Scan|Index Scan|Bitmap Heap Scan)( using \w+)?")


def load_queries() -> list[tuple[str, str]]:
    text = (HERE / "queries.sql").read_text()
    parts = re.split(r"^-- name: (.+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def explain(cur, sql: str, params: dict) -> tuple[list[str], float]:
    """Run EXPLAIN ANALYZE twice and keep the second run (the first warms the cache)."""
    for _ in range(2):
        cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
        lines = [r[0] for r in cur.fetchall()]
    ms = float(re.search(r"Execution Time: ([\d.]+) ms", lines[-1]).group(1))
    return lines, ms


def scans(plan: list[str]) -> str:
    found = []
    for line in plan:
        m = SCAN_RE.search(line)
        if m:
            found.append((m.group(1) + (m.group(2) or "")).strip())
    return " + ".join(dict.fromkeys(found)) or "?"


def main() -> None:
    cleanup = "--cleanup" in sys.argv
    queries = load_queries()
    # ClientCursor fills %(name)s placeholders safely on the client, which EXPLAIN needs
    # (server-side parameters would make the planner use a generic plan).
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        cur = psycopg.ClientCursor(conn)
        print("Building perf_demo data (generate_series runs inside Postgres)...")
        cur.execute((HERE / "01_setup.sql").read_text())
        cur.execute("SET jit = off")  # JIT compile time would drown out millisecond queries
        today = cur.execute("SELECT today FROM public.app_clock").fetchone()[0]
        n_inv = cur.execute("SELECT count(*) FROM perf_demo.invoices").fetchone()[0]
        n_pay = cur.execute("SELECT count(*) FROM perf_demo.payments").fetchone()[0]
        n_open = cur.execute("SELECT count(*) FROM perf_demo.invoices WHERE status = 'CONFIRMED'").fetchone()[0]
        invoice_id = cur.execute("SELECT invoice_id FROM perf_demo.payments ORDER BY id OFFSET 40000 LIMIT 1").fetchone()[0]
        params = {"today": today, "customer_id": 4242, "invoice_id": invoice_id, "pattern": "%Company 4242 %"}

        # The setup script created the indexes; read their definitions so we can show them.
        defs = dict(cur.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'perf_demo'"
        ).fetchall())

        results = {}
        for label in ("with", "without"):
            if label == "without":
                for name in SECONDARY_INDEXES:
                    cur.execute(f"DROP INDEX perf_demo.{name}")  # names come from the constant above, not user input
                cur.execute("ANALYZE perf_demo.invoices")
            for name, sql in queries:
                print(f"  [{label:7}] {name}")
                results[(label, name)] = explain(cur, sql, params)

        out = [
            "# Query plans: with vs without indexes",
            "",
            f"Data: `perf_demo` schema, {n_inv:,} invoices ({n_open:,} open), {n_pay:,} payments, "
            f"10,000 customers, 30,000 subscriptions. Clock: {today}.",
            "Times are `EXPLAIN (ANALYZE, BUFFERS)` execution time on the database server "
            "(second of two runs), so network latency is not included.",
            "",
            "| Query | Without indexes | Plan | With indexes | Plan | Speed-up |",
            "|---|---:|---|---:|---|---:|",
        ]
        for name, _ in queries:
            (wp, wms), (ip, ims) = results[("without", name)], results[("with", name)]
            out.append(f"| {name} | {wms:.2f} ms | {scans(wp)} | {ims:.2f} ms | {scans(ip)} | {wms / max(ims, 0.01):.0f}x |")
        out += ["", "## Indexes under test", "", "```sql", *[defs[n] + ";" for n in SECONDARY_INDEXES if n in defs], "```"]
        out += ["", "## Full plans", ""]
        for name, sql in queries:
            out += [f"### {name}", "", "```sql", sql, "```", ""]
            for label in ("without", "with"):
                out += [f"**{label} indexes**", "", "```", *results[(label, name)][0], "```", ""]
        (HERE / "results.md").write_text("\n".join(out))
        print("Wrote database/explain/results.md")

        if cleanup:
            cur.execute("DROP SCHEMA perf_demo CASCADE")
            print("Dropped schema perf_demo")


if __name__ == "__main__":
    main()
