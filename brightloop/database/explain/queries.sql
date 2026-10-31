-- Each block is one query the app really runs. The runner executes it WITH and
-- WITHOUT the secondary indexes. Parameters: %(today)s, %(customer_id)s, %(invoice_id)s.
-- Same logic as the views in 001_init.sql, pointed at perf_demo.* tables.

-- name: Overdue list (dashboard hero table)
SELECT i.id, i.number, c.company_name, i.due_date, i.total - i.amount_paid AS balance
  FROM perf_demo.invoices i
  JOIN perf_demo.customers c ON c.id = i.customer_id
 WHERE i.status = 'CONFIRMED' AND i.due_date < %(today)s AND i.amount_paid < i.total
 ORDER BY i.due_date
 LIMIT 25;

-- name: Outstanding amount (dashboard KPI)
SELECT COALESCE(SUM(total - amount_paid), 0) AS outstanding
  FROM perf_demo.invoices
 WHERE status = 'CONFIRMED';

-- name: Customer portal: my latest invoices
SELECT id, number, status, issue_date, total
  FROM perf_demo.invoices
 WHERE customer_id = %(customer_id)s
 ORDER BY issue_date DESC
 LIMIT 25;

-- name: Payments for one invoice
SELECT id, method, amount, paid_on
  FROM perf_demo.payments
 WHERE invoice_id = %(invoice_id)s;

-- name: Collected this month (dashboard KPI)
SELECT COALESCE(SUM(amount), 0) AS collected
  FROM perf_demo.payments
 WHERE paid_on >= date_trunc('month', %(today)s::date)::date AND paid_on <= %(today)s;

-- name: Billing engine: who is due today?
SELECT id, customer_id, next_billing_date
  FROM perf_demo.subscriptions
 WHERE status = 'ACTIVE' AND next_billing_date <= %(today)s
 ORDER BY id;

-- name: Customer search (name contains "Company 4242 ")
SELECT id, company_name
  FROM perf_demo.customers
 WHERE company_name ILIKE %(pattern)s
 LIMIT 25;
