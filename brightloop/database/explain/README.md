# Query plans: indexes vs sequential scans

The "why is it fast?" slide. One command rebuilds the data, measures every query with and
without its indexes, and writes the evidence to [`results.md`](results.md).

```bash
source backend/.venv/bin/activate
python database/explain/run_explain.py            # ~10 seconds; keeps perf_demo for live demos
python database/explain/run_explain.py --cleanup  # same, then DROP SCHEMA perf_demo
```

| File | What it is |
|---|---|
| `01_setup.sql` | Creates schema `perf_demo`, bulk-loads ~150k invoices, ~138k payments, 10k customers, 30k subscriptions with `generate_series` |
| `queries.sql` | The 7 queries the app really runs (dashboard, portal, billing, search) |
| `run_explain.py` | Runs each query twice per mode, keeps the second run, writes `results.md` |

## Why a separate schema

To show "without index" we have to DROP the indexes. Doing that to the real tables would break the
shared database. `perf_demo.*` copies the real table shapes (including every CHECK constraint, so
the generated money has to add up) and is isolated: `DROP SCHEMA perf_demo CASCADE;` removes all of it.
It also never touches the real `invoice_number_seq`.

## What to say in the demo

- Primary keys and UNIQUE constraints stay in both runs, they protect data. Only the performance
  indexes are dropped.
- `idx_invoices_open` is a **partial index** (`WHERE status = 'CONFIRMED'`). About 4% of invoices are
  open, so the index is tiny, and the overdue list reads 25 index entries instead of 150,000 rows.
- `idx_invoices_customer (customer_id, issue_date DESC)` serves the portal list with no sort step.
- `gin_trgm_ops` makes `ILIKE '%text%'` search indexable, which a normal B-tree cannot do.
- The two KPI sums gain least (2x to 4x) because they must read many rows anyway. That is honest
  and worth saying out loud.
- Times are server-side. The real database is remote, so every request also pays 50-200 ms of network,
  which is why the code never runs a query inside a loop.
