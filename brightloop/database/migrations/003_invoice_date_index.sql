-- =============================================================================
-- 003_invoice_date_index.sql  --  index for the invoice list date filter
--
-- WHY: GET /invoices?from=...&to=... filters on issue_date across ALL customers.
-- idx_invoices_customer is (customer_id, issue_date), so it only helps when a
-- customer is also chosen. Without this index the date filter scans every
-- invoice. This is also a good "index vs sequential scan" EXPLAIN ANALYZE demo.
--
-- No new tables here, so 002_lock_public_api.sql does not need re-running.
-- =============================================================================

CREATE INDEX idx_invoices_issue_date ON invoices (issue_date DESC);
