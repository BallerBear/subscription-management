-- =============================================================================
-- PERFORMANCE DEMO DATA  (schema perf_demo)
--
-- WHY A SEPARATE SCHEMA: to show "with index vs without index" we must DROP the
-- indexes. Doing that on the real tables would break the shared database for the
-- team. perf_demo.* are copies of the real table shapes, filled with bulk data
-- and removable with:   DROP SCHEMA perf_demo CASCADE;
--
-- Rows are generated INSIDE Postgres with generate_series (one statement per
-- table), so no data travels over the network. Every CHECK constraint of the real
-- invoices/payments tables is copied (LIKE ... INCLUDING CONSTRAINTS), so if the
-- generated money did not add up, the load itself would fail.
-- =============================================================================

DROP SCHEMA IF EXISTS perf_demo CASCADE;
CREATE SCHEMA perf_demo;

-- ---- customers: only the columns the queries touch ---------------------------
CREATE TABLE perf_demo.customers (
  id           BIGINT PRIMARY KEY,
  company_name TEXT NOT NULL
);

-- ---- subscriptions: only what the billing "who is due?" query touches --------
CREATE TABLE perf_demo.subscriptions (
  id                BIGINT PRIMARY KEY,
  customer_id       BIGINT NOT NULL,
  status            public.subscription_status_t NOT NULL,
  next_billing_date DATE
);

-- ---- invoices / payments: same columns and CHECKs as the real tables ---------
-- No defaults are copied, so loading never touches the real invoice number sequence.
CREATE TABLE perf_demo.invoices (LIKE public.invoices INCLUDING CONSTRAINTS);
ALTER TABLE perf_demo.invoices
  ADD PRIMARY KEY (id),
  ADD UNIQUE (number),
  ADD CONSTRAINT one_invoice_per_period UNIQUE (subscription_id, period_start);

-- Only the timestamp defaults are restored (the NOT NULL columns need a value).
ALTER TABLE perf_demo.invoices
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET DEFAULT now();

CREATE TABLE perf_demo.payments (LIKE public.payments INCLUDING CONSTRAINTS);
ALTER TABLE perf_demo.payments ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE perf_demo.payments ADD PRIMARY KEY (id);

-- ---- bulk load ---------------------------------------------------------------
-- 10,000 customers
INSERT INTO perf_demo.customers
SELECT g,
       'Company ' || g || ' ' || (ARRAY['Technologies','Systems','Labs','Traders','Logistics','Textiles'])[1 + g % 6]
  FROM generate_series(1, 10000) g;

-- 30,000 subscriptions; about 2% are due for billing today
INSERT INTO perf_demo.subscriptions
SELECT g,
       1 + g % 10000,
       (CASE WHEN g % 10 < 7 THEN 'ACTIVE' WHEN g % 10 < 9 THEN 'CLOSED' ELSE 'PAUSED' END)::public.subscription_status_t,
       (SELECT today FROM public.app_clock) - 5 + (g % 300)
  FROM generate_series(1, 30000) g;

-- 150,000 invoices = 5 monthly periods x 30,000 subscriptions.
-- Old invoices are almost all PAID; only recent ones are still CONFIRMED (open),
-- plus a thin tail of long-overdue ones. That is what real billing data looks like,
-- and it is why a PARTIAL index on open invoices is so small and effective.
WITH base AS (
  SELECT g,
         1 + (g - 1) % 30000                    AS sub_id,
         (g - 1) / 30000                        AS k,             -- period 0 (oldest) .. 4 (newest)
         (SELECT today FROM public.app_clock)   AS today,
         100000 + (g * 7919) % 900000           AS subtotal       -- Rs 1,000 .. Rs 10,000 in paise
    FROM generate_series(1, 150000) g
), shaped AS (
  SELECT *,
         (today - 150 + k * 30 + (sub_id % 28))::DATE AS issue,
         (subtotal * 1800 + 5000) / 10000            AS tax,      -- 18% in basis points, rounded
         CASE WHEN g % 100 < 3 THEN 'DRAFT'
              WHEN g % 100 < 5 THEN 'CANCELLED'
              WHEN k = 4 AND g % 100 < 15 THEN 'CONFIRMED'
              WHEN k = 3 AND g % 100 < 9  THEN 'CONFIRMED'
              WHEN g % 100 = 99           THEN 'CONFIRMED'        -- long-overdue tail
              ELSE 'PAID' END                           AS st
    FROM base
)
INSERT INTO perf_demo.invoices
  (id, number, subscription_id, customer_id, status, period_start, period_end,
   issue_date, due_date, subtotal, discount_total, tax_total, total, amount_paid)
SELECT g,
       'INV-' || lpad(g::TEXT, 6, '0'),
       sub_id,
       1 + sub_id % 10000,
       st::public.invoice_status_t,
       issue,
       (issue + INTERVAL '1 month')::DATE,
       issue,
       issue + 30,
       subtotal, 0, tax, subtotal + tax,
       CASE st WHEN 'PAID' THEN subtotal + tax
               WHEN 'CONFIRMED' THEN CASE WHEN g % 4 = 0 THEN (subtotal + tax) / 2 ELSE 0 END
               ELSE 0 END
  FROM shaped;

-- One payment for every invoice that has money on it, never dated after "today".
INSERT INTO perf_demo.payments (id, invoice_id, method, amount, paid_on, reference)
SELECT row_number() OVER (ORDER BY i.id),
       i.id,
       (ARRAY['CARD','UPI','BANK_TRANSFER','CASH','CHEQUE'])[1 + (i.id % 5)]::public.payment_method_t,
       i.amount_paid,
       LEAST(i.issue_date + (i.id % 25)::INT, (SELECT today FROM public.app_clock)),
       'REF' || i.id
  FROM perf_demo.invoices i
 WHERE i.amount_paid > 0;

-- Same secondary indexes as 001_init.sql / 003 (names match the real ones).
-- The runner drops exactly these for the "without indexes" measurement.
CREATE INDEX idx_customers_company_trgm ON perf_demo.customers USING gin (company_name gin_trgm_ops);
CREATE INDEX idx_subscriptions_due      ON perf_demo.subscriptions (next_billing_date) WHERE status = 'ACTIVE';
CREATE INDEX idx_invoices_customer      ON perf_demo.invoices (customer_id, issue_date DESC);
CREATE INDEX idx_invoices_status        ON perf_demo.invoices (status);
CREATE INDEX idx_invoices_open          ON perf_demo.invoices (due_date) WHERE status = 'CONFIRMED';
CREATE INDEX idx_invoices_issue_date    ON perf_demo.invoices (issue_date DESC);
CREATE INDEX idx_payments_invoice       ON perf_demo.payments (invoice_id);
CREATE INDEX idx_payments_paid_on       ON perf_demo.payments (paid_on);

-- Without fresh statistics the planner guesses badly. The real database does this
-- automatically (autovacuum); here we do it by hand because we just loaded 400k rows.
ANALYZE perf_demo.customers;
ANALYZE perf_demo.subscriptions;
ANALYZE perf_demo.invoices;
ANALYZE perf_demo.payments;
