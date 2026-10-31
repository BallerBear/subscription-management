# Query plans: with vs without indexes

Data: `perf_demo` schema, 150,000 invoices (5,700 open), 137,700 payments, 10,000 customers, 30,000 subscriptions. Clock: 2026-11-30.
Times are `EXPLAIN (ANALYZE, BUFFERS)` execution time on the database server (second of two runs), so network latency is not included.

| Query | Without indexes | Plan | With indexes | Plan | Speed-up |
|---|---:|---|---:|---|---:|
| Overdue list (dashboard hero table) | 21.77 ms | Seq Scan + Index Scan using customers_pkey | 0.17 ms | Index Scan using idx_invoices_open + Index Scan using customers_pkey | 127x |
| Outstanding amount (dashboard KPI) | 18.33 ms | Seq Scan | 4.76 ms | Index Scan using idx_invoices_open | 4x |
| Customer portal: my latest invoices | 18.04 ms | Seq Scan | 0.06 ms | Index Scan using idx_invoices_customer | 296x |
| Payments for one invoice | 12.97 ms | Seq Scan | 0.07 ms | Index Scan using idx_payments_invoice | 191x |
| Collected this month (dashboard KPI) | 38.10 ms | Seq Scan | 15.72 ms | Index Scan using idx_payments_paid_on | 2x |
| Billing engine: who is due today? | 2.74 ms | Seq Scan | 0.43 ms | Bitmap Heap Scan + Index Scan | 6x |
| Customer search (name contains "Company 4242 ") | 13.28 ms | Seq Scan | 0.44 ms | Bitmap Heap Scan + Index Scan | 30x |

## Indexes under test

```sql
CREATE INDEX idx_customers_company_trgm ON perf_demo.customers USING gin (company_name gin_trgm_ops);
CREATE INDEX idx_subscriptions_due ON perf_demo.subscriptions USING btree (next_billing_date) WHERE (status = 'ACTIVE'::subscription_status_t);
CREATE INDEX idx_invoices_customer ON perf_demo.invoices USING btree (customer_id, issue_date DESC);
CREATE INDEX idx_invoices_status ON perf_demo.invoices USING btree (status);
CREATE INDEX idx_invoices_open ON perf_demo.invoices USING btree (due_date) WHERE (status = 'CONFIRMED'::invoice_status_t);
CREATE INDEX idx_invoices_issue_date ON perf_demo.invoices USING btree (issue_date DESC);
CREATE INDEX idx_payments_invoice ON perf_demo.payments USING btree (invoice_id);
CREATE INDEX idx_payments_paid_on ON perf_demo.payments USING btree (paid_on);
```

## Full plans

### Overdue list (dashboard hero table)

```sql
SELECT i.id, i.number, c.company_name, i.due_date, i.total - i.amount_paid AS balance
  FROM perf_demo.invoices i
  JOIN perf_demo.customers c ON c.id = i.customer_id
 WHERE i.status = 'CONFIRMED' AND i.due_date < %(today)s AND i.amount_paid < i.total
 ORDER BY i.due_date
 LIMIT 25;
```

**without indexes**

```
Limit  (cost=5471.83..5484.32 rows=25 width=52) (actual time=17.497..21.705 rows=25 loops=1)
  Buffers: shared hit=2998
  ->  Nested Loop  (cost=5471.83..6206.96 rows=1472 width=52) (actual time=17.496..21.697 rows=25 loops=1)
        Buffers: shared hit=2998
        ->  Gather Merge  (cost=5471.55..5639.88 rows=1477 width=47) (actual time=17.469..20.368 rows=25 loops=1)
              Workers Planned: 1
              Workers Launched: 1
              Buffers: shared hit=2923
              ->  Sort  (cost=4471.54..4473.71 rows=869 width=47) (actual time=14.516..14.543 rows=363 loops=2)
                    Sort Key: i.due_date
                    Sort Method: quicksort  Memory: 155kB
                    Buffers: shared hit=2923
                    Worker 0:  Sort Method: quicksort  Memory: 68kB
                    ->  Parallel Seq Scan on invoices i  (cost=0.00..4429.12 rows=869 width=47) (actual time=0.032..14.128 rows=1200 loops=2)
                          Filter: ((due_date < '2026-11-30'::date) AND (amount_paid < total) AND (status = 'CONFIRMED'::invoice_status_t))
                          Rows Removed by Filter: 73800
                          Buffers: shared hit=2885
        ->  Index Scan using customers_pkey on customers c  (cost=0.29..0.38 rows=1 width=29) (actual time=0.051..0.051 rows=1 loops=25)
              Index Cond: (id = i.customer_id)
              Buffers: shared hit=75
Planning:
  Buffers: shared hit=6
Planning Time: 0.203 ms
Execution Time: 21.766 ms
```

**with indexes**

```
Limit  (cost=0.57..16.57 rows=25 width=52) (actual time=0.021..0.141 rows=25 loops=1)
  Buffers: shared hit=102
  ->  Nested Loop  (cost=0.57..967.26 rows=1510 width=52) (actual time=0.020..0.137 rows=25 loops=1)
        Buffers: shared hit=102
        ->  Index Scan using idx_invoices_open on invoices i  (cost=0.28..390.11 rows=1510 width=47) (actual time=0.014..0.045 rows=25 loops=1)
              Index Cond: (due_date < '2026-11-30'::date)
              Filter: (amount_paid < total)
              Buffers: shared hit=27
        ->  Index Scan using customers_pkey on customers c  (cost=0.29..0.38 rows=1 width=29) (actual time=0.003..0.003 rows=1 loops=25)
              Index Cond: (id = i.customer_id)
              Buffers: shared hit=75
Planning:
  Buffers: shared hit=14
Planning Time: 0.276 ms
Execution Time: 0.172 ms
```

### Outstanding amount (dashboard KPI)

```sql
SELECT COALESCE(SUM(total - amount_paid), 0) AS outstanding
  FROM perf_demo.invoices
 WHERE status = 'CONFIRMED';
```

**without indexes**

```
Aggregate  (cost=4787.75..4787.76 rows=1 width=32) (actual time=18.295..18.296 rows=1 loops=1)
  Buffers: shared hit=2885
  ->  Seq Scan on invoices  (cost=0.00..4760.00 rows=5550 width=16) (actual time=0.025..17.502 rows=5700 loops=1)
        Filter: (status = 'CONFIRMED'::invoice_status_t)
        Rows Removed by Filter: 144300
        Buffers: shared hit=2885
Planning Time: 0.087 ms
Execution Time: 18.328 ms
```

**with indexes**

```
Aggregate  (cost=462.43..462.44 rows=1 width=32) (actual time=4.736..4.736 rows=1 loops=1)
  Buffers: shared hit=5706
  ->  Index Scan using idx_invoices_open on invoices  (cost=0.28..433.93 rows=5700 width=16) (actual time=0.012..3.690 rows=5700 loops=1)
        Buffers: shared hit=5706
Planning Time: 0.092 ms
Execution Time: 4.765 ms
```

### Customer portal: my latest invoices

```sql
SELECT id, number, status, issue_date, total
  FROM perf_demo.invoices
 WHERE customer_id = %(customer_id)s
 ORDER BY issue_date DESC
 LIMIT 25;
```

**without indexes**

```
Limit  (cost=4760.29..4760.33 rows=15 width=35) (actual time=18.004..18.008 rows=15 loops=1)
  Buffers: shared hit=2885
  ->  Sort  (cost=4760.29..4760.33 rows=15 width=35) (actual time=18.003..18.005 rows=15 loops=1)
        Sort Key: issue_date DESC
        Sort Method: quicksort  Memory: 26kB
        Buffers: shared hit=2885
        ->  Seq Scan on invoices  (cost=0.00..4760.00 rows=15 width=35) (actual time=0.496..17.979 rows=15 loops=1)
              Filter: (customer_id = 4242)
              Rows Removed by Filter: 149985
              Buffers: shared hit=2885
Planning Time: 0.090 ms
Execution Time: 18.039 ms
```

**with indexes**

```
Limit  (cost=0.42..18.24 rows=15 width=35) (actual time=0.016..0.040 rows=15 loops=1)
  Buffers: shared hit=18
  ->  Index Scan using idx_invoices_customer on invoices  (cost=0.42..18.24 rows=15 width=35) (actual time=0.015..0.036 rows=15 loops=1)
        Index Cond: (customer_id = 4242)
        Buffers: shared hit=18
Planning Time: 0.112 ms
Execution Time: 0.061 ms
```

### Payments for one invoice

```sql
SELECT id, method, amount, paid_on
  FROM perf_demo.payments
 WHERE invoice_id = %(invoice_id)s;
```

**without indexes**

```
Seq Scan on payments  (cost=0.00..3286.25 rows=1 width=24) (actual time=3.673..12.930 rows=1 loops=1)
  Filter: (invoice_id = 42555)
  Rows Removed by Filter: 137699
  Buffers: shared hit=1565
Planning Time: 0.057 ms
Execution Time: 12.967 ms
```

**with indexes**

```
Index Scan using idx_payments_invoice on payments  (cost=0.42..2.64 rows=1 width=24) (actual time=0.016..0.016 rows=1 loops=1)
  Index Cond: (invoice_id = 42555)
  Buffers: shared hit=4
Planning Time: 0.070 ms
Execution Time: 0.068 ms
```

### Collected this month (dashboard KPI)

```sql
SELECT COALESCE(SUM(amount), 0) AS collected
  FROM perf_demo.payments
 WHERE paid_on >= date_trunc('month', %(today)s::date)::date AND paid_on <= %(today)s;
```

**without indexes**

```
Finalize Aggregate  (cost=4440.85..4440.86 rows=1 width=32) (actual time=34.261..38.063 rows=1 loops=1)
  Buffers: shared hit=1565
  ->  Gather  (cost=4440.73..4440.84 rows=1 width=32) (actual time=34.118..38.029 rows=2 loops=1)
        Workers Planned: 1
        Workers Launched: 1
        Buffers: shared hit=1565
        ->  Partial Aggregate  (cost=3440.73..3440.74 rows=1 width=32) (actual time=31.127..31.128 rows=1 loops=2)
              Buffers: shared hit=1565
              ->  Parallel Seq Scan on payments  (cost=0.00..3387.50 rows=21291 width=8) (actual time=17.694..29.775 rows=17678 loops=2)
                    Filter: ((paid_on <= '2026-11-30'::date) AND (paid_on >= (date_trunc('month'::text, ('2026-11-30'::date)::timestamp with time zone))::date))
                    Rows Removed by Filter: 51172
                    Buffers: shared hit=1565
Planning Time: 0.101 ms
Execution Time: 38.102 ms
```

**with indexes**

```
Aggregate  (cost=1380.46..1380.47 rows=1 width=32) (actual time=15.684..15.685 rows=1 loops=1)
  Buffers: shared hit=12713
  ->  Index Scan using idx_payments_paid_on on payments  (cost=0.30..1289.95 rows=36202 width=8) (actual time=0.018..11.860 rows=35355 loops=1)
        Index Cond: ((paid_on >= (date_trunc('month'::text, ('2026-11-30'::date)::timestamp with time zone))::date) AND (paid_on <= '2026-11-30'::date))
        Buffers: shared hit=12713
Planning:
  Buffers: shared hit=3
Planning Time: 0.128 ms
Execution Time: 15.721 ms
```

### Billing engine: who is due today?

```sql
SELECT id, customer_id, next_billing_date
  FROM perf_demo.subscriptions
 WHERE status = 'ACTIVE' AND next_billing_date <= %(today)s
 ORDER BY id;
```

**without indexes**

```
Sort  (cost=660.35..661.40 rows=421 width=20) (actual time=2.641..2.677 rows=600 loops=1)
  Sort Key: id
  Sort Method: quicksort  Memory: 48kB
  Buffers: shared hit=192
  ->  Seq Scan on subscriptions  (cost=0.00..642.00 rows=421 width=20) (actual time=0.016..2.531 rows=600 loops=1)
        Filter: ((next_billing_date <= '2026-11-30'::date) AND (status = 'ACTIVE'::subscription_status_t))
        Rows Removed by Filter: 29400
        Buffers: shared hit=192
Planning Time: 0.089 ms
Execution Time: 2.736 ms
```

**with indexes**

```
Sort  (cost=221.32..222.37 rows=421 width=20) (actual time=0.334..0.369 rows=600 loops=1)
  Sort Key: id
  Sort Method: quicksort  Memory: 48kB
  Buffers: shared hit=105
  ->  Bitmap Heap Scan on subscriptions  (cost=4.65..202.97 rows=421 width=20) (actual time=0.043..0.245 rows=600 loops=1)
        Recheck Cond: ((next_billing_date <= '2026-11-30'::date) AND (status = 'ACTIVE'::subscription_status_t))
        Heap Blocks: exact=103
        Buffers: shared hit=105
        ->  Bitmap Index Scan on idx_subscriptions_due  (cost=0.00..4.54 rows=421 width=0) (actual time=0.025..0.025 rows=600 loops=1)
              Index Cond: (next_billing_date <= '2026-11-30'::date)
              Buffers: shared hit=2
Planning Time: 0.099 ms
Execution Time: 0.426 ms
```

### Customer search (name contains "Company 4242 ")

```sql
SELECT id, company_name
  FROM perf_demo.customers
 WHERE company_name ILIKE %(pattern)s
 LIMIT 25;
```

**without indexes**

```
Limit  (cost=0.00..201.00 rows=1 width=29) (actual time=5.571..13.258 rows=1 loops=1)
  Buffers: shared hit=76
  ->  Seq Scan on customers  (cost=0.00..201.00 rows=1 width=29) (actual time=5.570..13.257 rows=1 loops=1)
        Filter: (company_name ~~* '%Company 4242 %'::text)
        Rows Removed by Filter: 9999
        Buffers: shared hit=76
Planning Time: 0.193 ms
Execution Time: 13.281 ms
```

**with indexes**

```
Limit  (cost=32.94..34.05 rows=1 width=29) (actual time=0.417..0.418 rows=1 loops=1)
  Buffers: shared hit=48
  ->  Bitmap Heap Scan on customers  (cost=32.94..34.05 rows=1 width=29) (actual time=0.416..0.416 rows=1 loops=1)
        Recheck Cond: (company_name ~~* '%Company 4242 %'::text)
        Heap Blocks: exact=1
        Buffers: shared hit=48
        ->  Bitmap Index Scan on idx_customers_company_trgm  (cost=0.00..32.94 rows=1 width=0) (actual time=0.403..0.403 rows=1 loops=1)
              Index Cond: (company_name ~~* '%Company 4242 %'::text)
              Buffers: shared hit=47
Planning:
  Buffers: shared hit=1
Planning Time: 0.253 ms
Execution Time: 0.444 ms
```
