-- Initial database migration.
-- Add domain tables here as the billing schema is defined.
-- =============================================================================
-- 001_init.sql  --  Brightloop Subscription Management System
-- PostgreSQL 14+ (designed on 16)
--
-- HOW TO READ THIS FILE
--   0. Types, sequences, system tables
--   1. Identity       users, password_resets, customers
--   2. Catalog        taxes, products, variants, payment terms, plans,
--                     discounts, quotation templates
--   3. Subscriptions  subscriptions, lines, discount links, event history
--   4. Billing        invoices, invoice lines, payments, discount redemptions
--   5. System         audit log
--   6. Triggers       the rules the DATABASE enforces by itself
--   7. Indexes
--   8. Views          overdue, MRR, dashboard KPIs
--
-- CONVENTIONS
--   * Money = BIGINT in paise (Rs 1,499.00 = 149900). Never FLOAT for money.
--     BIGINT, not INTEGER: INTEGER overflows at ~Rs 2.1 crore.
--   * Tax rates and percent discounts = integer basis points (18% = 1800).
--   * Business dates are DATE, and "today" comes from app_clock (the Time
--     Machine), never from CURRENT_DATE.
--   * Financial rows are never DELETEd. We flag (is_active) or cancel.
--   * ONE rounding rule everywhere: half-up on whole paise
--       tax = (amount * rate_bps + 5000) / 10000     (integer division)
--   * The migration runner wraps this file in a transaction, so there is no
--     BEGIN/COMMIT in here.
-- =============================================================================


-- =============================================================================
-- 0. TYPES, SEQUENCES, SYSTEM TABLES
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fast "contains" search on names

CREATE TYPE role_t                AS ENUM ('ADMIN', 'STAFF', 'CUSTOMER');
CREATE TYPE product_type_t        AS ENUM ('SOFTWARE', 'ADD_ON', 'SERVICE');
CREATE TYPE billing_period_t      AS ENUM ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY');
CREATE TYPE discount_type_t       AS ENUM ('FIXED', 'PERCENT');
CREATE TYPE discount_scope_t      AS ENUM ('PRODUCT', 'SUBSCRIPTION');
CREATE TYPE subscription_status_t AS ENUM ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED');
CREATE TYPE invoice_status_t      AS ENUM ('DRAFT', 'CONFIRMED', 'PAID', 'CANCELLED');
CREATE TYPE payment_method_t      AS ENUM ('CARD', 'UPI', 'BANK_TRANSFER', 'CASH', 'CHEQUE');

-- Sequences hand out numbers atomically. "COUNT(*) + 1" breaks when two
-- people create a record at the same moment; a sequence never does.
CREATE SEQUENCE subscription_number_seq START 1;
CREATE SEQUENCE invoice_number_seq      START 1;

-- The Time Machine. Exactly ONE row, enforced by the boolean primary key:
-- "singleton" can only ever be TRUE, so a second row would collide.
CREATE TABLE app_clock (
  singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
  today     DATE    NOT NULL DEFAULT CURRENT_DATE
);
INSERT INTO app_clock DEFAULT VALUES;

-- The state machines stored as DATA. One trigger (section 6) reads this table.
-- The UI can read it too, so buttons are generated from the same source of truth.
-- action_label NULL = system-driven move with no button (e.g. CONFIRMED -> PAID
-- happens automatically when the last payment arrives).
CREATE TABLE status_transitions (
  entity       TEXT NOT NULL CHECK (entity IN ('SUBSCRIPTION', 'INVOICE')),
  from_status  TEXT NOT NULL,
  to_status    TEXT NOT NULL,
  action_label TEXT,
  PRIMARY KEY (entity, from_status, to_status)
);

INSERT INTO status_transitions (entity, from_status, to_status, action_label) VALUES
  ('SUBSCRIPTION', 'DRAFT',     'QUOTATION', 'Create quotation'),
  ('SUBSCRIPTION', 'DRAFT',     'CLOSED',    'Discard'),
  ('SUBSCRIPTION', 'QUOTATION', 'DRAFT',     'Back to draft'),
  ('SUBSCRIPTION', 'QUOTATION', 'CONFIRMED', 'Confirm'),
  ('SUBSCRIPTION', 'QUOTATION', 'CLOSED',    'Cancel quotation'),
  ('SUBSCRIPTION', 'CONFIRMED', 'ACTIVE',    'Activate'),
  ('SUBSCRIPTION', 'CONFIRMED', 'CLOSED',    'Close'),
  ('SUBSCRIPTION', 'ACTIVE',    'PAUSED',    'Pause'),
  ('SUBSCRIPTION', 'ACTIVE',    'CLOSED',    'Close'),
  ('SUBSCRIPTION', 'PAUSED',    'ACTIVE',    'Resume'),
  ('SUBSCRIPTION', 'PAUSED',    'CLOSED',    'Close'),
  ('INVOICE',      'DRAFT',     'CONFIRMED', 'Confirm'),
  ('INVOICE',      'DRAFT',     'CANCELLED', 'Cancel'),
  ('INVOICE',      'CONFIRMED', 'PAID',      NULL),
  ('INVOICE',      'CONFIRMED', 'CANCELLED', 'Cancel');


-- =============================================================================
-- 1. IDENTITY
-- =============================================================================

CREATE TABLE users (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email         TEXT   NOT NULL
                CONSTRAINT users_email_format CHECK (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  password_hash TEXT   NOT NULL,                       -- bcrypt hash, never the password
  name          TEXT   NOT NULL CHECK (length(btrim(name)) > 0),
  role          role_t NOT NULL DEFAULT 'CUSTOMER',    -- public signup can only ever be CUSTOMER
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Functional unique index: Soorya@x.com and soorya@x.com are the SAME account.
CREATE UNIQUE INDEX users_email_unique ON users (lower(email));

-- We store only a HASH of the reset token, so a leaked DB can't be used to
-- reset passwords. used_at makes each link single-use.
CREATE TABLE password_resets (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  token_hash TEXT   NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A customer is a BUSINESS. user_id is nullable: staff can create a customer
-- who has no portal login yet. UNIQUE allows many NULLs but only one customer
-- per user.
CREATE TABLE customers (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      BIGINT UNIQUE REFERENCES users (id),
  company_name TEXT NOT NULL CHECK (length(btrim(company_name)) > 0),
  contact_name TEXT NOT NULL,
  email        TEXT NOT NULL CHECK (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  phone        TEXT CHECK (phone IS NULL OR phone ~ '^[0-9+ -]{7,15}$'),
  address_line TEXT,
  city         TEXT,
  state        TEXT,
  postal_code  TEXT,
  country      TEXT NOT NULL DEFAULT 'India',
  gstin        TEXT CHECK (gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'),
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================================================
-- 2. CATALOG  (admin-managed)
-- =============================================================================

CREATE TABLE taxes (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name       TEXT    NOT NULL UNIQUE,                  -- 'GST 18%'
  rate_bps   INTEGER NOT NULL CHECK (rate_bps BETWEEN 0 AND 10000),   -- 1800 = 18%
  is_active  BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE products (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        TEXT NOT NULL CHECK (length(btrim(name)) > 0),
  type        product_type_t NOT NULL,
  sales_price BIGINT NOT NULL CHECK (sales_price >= 0),
  cost_price  BIGINT NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
  -- Generated column: the DB computes it, so it can never be out of date.
  margin      BIGINT GENERATED ALWAYS AS (sales_price - cost_price) STORED,
  notes       TEXT,
  tax_id      BIGINT NOT NULL REFERENCES taxes (id),
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX products_name_unique ON products (lower(name));

-- 'Brand = Odoo' adds 56000 paise (Rs 560) to the product price.
CREATE TABLE product_variants (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id  BIGINT NOT NULL REFERENCES products (id) ON DELETE CASCADE,
  attribute   TEXT   NOT NULL,                         -- 'Brand'
  value       TEXT   NOT NULL,                         -- 'Odoo'
  extra_price BIGINT NOT NULL DEFAULT 0 CHECK (extra_price >= 0),
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (product_id, attribute, value),
  -- Looks redundant (id is already unique) but it is the TARGET for the
  -- composite foreign keys below, which stop a line from pairing a product
  -- with some OTHER product's variant.
  UNIQUE (id, product_id)
);

-- "Payment terms" from the PDF, as an admin-editable lookup table.
CREATE TABLE payment_terms (
  id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT    NOT NULL UNIQUE,
  days INTEGER NOT NULL CHECK (days BETWEEN 0 AND 365)
);
INSERT INTO payment_terms (name, days) VALUES
  ('Due on receipt', 0), ('Net 15', 15), ('Net 30', 30), ('Net 45', 45);

-- ASSUMPTION (confirm with organizers): plan.price is a base fee billed as
-- its own invoice line each period, on top of the product lines.
CREATE TABLE plans (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name              TEXT NOT NULL CHECK (length(btrim(name)) > 0),
  price             BIGINT NOT NULL DEFAULT 0 CHECK (price >= 0),
  billing_period    billing_period_t NOT NULL,
  min_quantity      INTEGER NOT NULL DEFAULT 1 CHECK (min_quantity >= 1),
  available_from    DATE NOT NULL,
  available_to      DATE,                              -- NULL = open-ended
  tax_id            BIGINT REFERENCES taxes (id),      -- tax on the plan fee
  -- "The admin decides which, plan by plan": per-plan behaviour switches.
  -- The trigger in section 6 enforces them.
  auto_close        BOOLEAN NOT NULL DEFAULT FALSE,    -- closes itself at expiry
  allow_early_close BOOLEAN NOT NULL DEFAULT TRUE,
  allow_pause       BOOLEAN NOT NULL DEFAULT FALSE,
  allow_renew       BOOLEAN NOT NULL DEFAULT TRUE,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT plan_dates_ordered CHECK (available_to IS NULL OR available_to >= available_from),
  CONSTRAINT plan_fee_needs_tax CHECK (price = 0 OR tax_id IS NOT NULL)
);
CREATE UNIQUE INDEX plans_name_unique ON plans (lower(name));

-- Discount RULES. Only the admin creates these.
--   value     = paise when FIXED, basis points when PERCENT
--   usage_limit NULL = unlimited;  end_date NULL = no expiry
CREATE TABLE discounts (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name         TEXT NOT NULL CHECK (length(btrim(name)) > 0),
  type         discount_type_t  NOT NULL,
  value        BIGINT NOT NULL CHECK (value > 0),
  scope        discount_scope_t NOT NULL,
  product_id   BIGINT REFERENCES products (id),        -- only for scope PRODUCT
  min_purchase BIGINT  NOT NULL DEFAULT 0 CHECK (min_purchase >= 0),
  min_quantity INTEGER NOT NULL DEFAULT 0 CHECK (min_quantity >= 0),
  start_date   DATE NOT NULL,
  end_date     DATE,
  usage_limit  INTEGER CHECK (usage_limit IS NULL OR usage_limit > 0),
  times_used   INTEGER NOT NULL DEFAULT 0 CHECK (times_used >= 0),
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT discount_percent_range   CHECK (type <> 'PERCENT' OR value <= 10000),
  CONSTRAINT discount_dates_ordered   CHECK (end_date IS NULL OR end_date >= start_date),
  -- A PRODUCT discount must name a product; a SUBSCRIPTION discount must not.
  CONSTRAINT discount_scope_product   CHECK ((scope = 'PRODUCT') = (product_id IS NOT NULL)),
  -- Backstop: even if the app forgets to check, usage can never exceed the limit.
  CONSTRAINT discount_within_limit    CHECK (usage_limit IS NULL OR times_used <= usage_limit)
);

CREATE TABLE quotation_templates (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  validity_days INTEGER NOT NULL DEFAULT 30 CHECK (validity_days > 0),
  plan_id       BIGINT NOT NULL REFERENCES plans (id),
  notes         TEXT,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE quotation_template_lines (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES quotation_templates (id) ON DELETE CASCADE,
  product_id  BIGINT NOT NULL REFERENCES products (id),
  variant_id  BIGINT,
  quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
  -- Composite FK: (variant, product) must exist TOGETHER in product_variants.
  -- When variant_id is NULL the check is skipped (standard SQL MATCH SIMPLE).
  FOREIGN KEY (variant_id, product_id) REFERENCES product_variants (id, product_id)
);
-- One line per (template, product, variant). COALESCE makes NULL variants comparable.
CREATE UNIQUE INDEX qtl_unique_line
  ON quotation_template_lines (template_id, product_id, COALESCE(variant_id, 0));


-- =============================================================================
-- 3. SUBSCRIPTIONS
-- =============================================================================

CREATE TABLE subscriptions (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  number                TEXT NOT NULL UNIQUE
                        DEFAULT ('SUB-' || lpad(nextval('subscription_number_seq')::TEXT, 4, '0')),
  customer_id           BIGINT NOT NULL REFERENCES customers (id),
  plan_id               BIGINT NOT NULL REFERENCES plans (id),
  template_id           BIGINT REFERENCES quotation_templates (id) ON DELETE SET NULL,
  payment_term_id       BIGINT NOT NULL REFERENCES payment_terms (id),
  status                subscription_status_t NOT NULL DEFAULT 'DRAFT',
  start_date            DATE NOT NULL,
  expiry_date           DATE NOT NULL,
  quotation_valid_until DATE,                           -- today + template.validity_days
  next_billing_date     DATE,                           -- set on activation, advanced by billing
  created_by            BIGINT REFERENCES users (id),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT sub_dates_ordered CHECK (expiry_date > start_date),
  CONSTRAINT sub_active_has_billing_date CHECK (status <> 'ACTIVE' OR next_billing_date IS NOT NULL),
  -- Target for invoices' composite FK (see invoices).
  UNIQUE (id, customer_id)
);

-- Lines SNAPSHOT price and tax at the moment they are created, so future
-- price/tax edits never rewrite existing subscriptions.
-- product_id NULL = a custom line (e.g. the plan base fee).
CREATE TABLE subscription_lines (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions (id) ON DELETE CASCADE,
  product_id      BIGINT REFERENCES products (id),
  variant_id      BIGINT,
  description     TEXT    NOT NULL,                     -- 'Business Suite - Brand: Odoo'
  quantity        INTEGER NOT NULL CHECK (quantity > 0),
  unit_price      BIGINT  NOT NULL CHECK (unit_price >= 0),   -- product price + variant extra
  tax_name        TEXT    NOT NULL,
  tax_rate_bps    INTEGER NOT NULL CHECK (tax_rate_bps BETWEEN 0 AND 10000),
  -- The DB does the line math. The app never has to.
  line_subtotal   BIGINT GENERATED ALWAYS AS (quantity::BIGINT * unit_price) STORED,
  line_tax        BIGINT GENERATED ALWAYS AS ((quantity::BIGINT * unit_price * tax_rate_bps + 5000) / 10000) STORED,
  FOREIGN KEY (variant_id, product_id) REFERENCES product_variants (id, product_id),
  CONSTRAINT line_variant_needs_product CHECK (variant_id IS NULL OR product_id IS NOT NULL)
);

-- Many-to-many: a subscription can carry several discounts, a discount can
-- apply to many subscriptions. Eligibility (dates, minimums, usage) is
-- re-checked at every billing run.
CREATE TABLE subscription_discounts (
  subscription_id BIGINT NOT NULL REFERENCES subscriptions (id) ON DELETE CASCADE,
  discount_id     BIGINT NOT NULL REFERENCES discounts (id),
  added_by        BIGINT REFERENCES users (id),
  added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (subscription_id, discount_id)
);

-- "Anyone should be able to see where it stands" + a history timeline.
-- Written by a trigger, so it cannot be forgotten.
CREATE TABLE subscription_events (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions (id) ON DELETE CASCADE,
  from_status     subscription_status_t,                -- NULL for the creation event
  to_status       subscription_status_t NOT NULL,
  changed_by      BIGINT REFERENCES users (id),
  changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================================================
-- 4. BILLING
-- =============================================================================

CREATE TABLE invoices (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  number          TEXT NOT NULL UNIQUE
                  DEFAULT ('INV-' || lpad(nextval('invoice_number_seq')::TEXT, 6, '0')),
  subscription_id BIGINT NOT NULL,
  customer_id     BIGINT NOT NULL,
  status          invoice_status_t NOT NULL DEFAULT 'DRAFT',
  period_start    DATE NOT NULL,
  period_end      DATE NOT NULL,
  issue_date      DATE NOT NULL,
  due_date        DATE NOT NULL,
  -- Header totals are filled by a trigger that sums the lines (section 6).
  subtotal        BIGINT NOT NULL DEFAULT 0,
  discount_total  BIGINT NOT NULL DEFAULT 0,
  tax_total       BIGINT NOT NULL DEFAULT 0,
  total           BIGINT NOT NULL DEFAULT 0,
  -- Maintained ONLY by the payments trigger.
  amount_paid     BIGINT NOT NULL DEFAULT 0,
  notes           TEXT,
  sent_at         TIMESTAMPTZ,                          -- set when the invoice is "sent"
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- customer_id is deliberately copied from the subscription (fast portal
  -- queries). This composite FK guarantees the copy can never disagree.
  CONSTRAINT invoice_matches_subscription_customer
    FOREIGN KEY (subscription_id, customer_id) REFERENCES subscriptions (id, customer_id),

  -- THE anti-double-billing guarantee: one invoice per subscription per period.
  CONSTRAINT one_invoice_per_period UNIQUE (subscription_id, period_start),

  CONSTRAINT invoice_period_valid       CHECK (period_end > period_start),
  CONSTRAINT invoice_due_after_issue    CHECK (due_date >= issue_date),
  CONSTRAINT invoice_money_nonneg       CHECK (subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0),
  CONSTRAINT invoice_discount_le_subtotal CHECK (discount_total <= subtotal),
  CONSTRAINT invoice_totals_add_up      CHECK (total = subtotal - discount_total + tax_total),
  CONSTRAINT invoice_paid_in_range      CHECK (amount_paid BETWEEN 0 AND total),
  CONSTRAINT invoice_paid_means_full    CHECK (status <> 'PAID' OR amount_paid = total),
  CONSTRAINT invoice_no_money_on_draft  CHECK (status NOT IN ('DRAFT', 'CANCELLED') OR amount_paid = 0)
);

-- The app supplies quantity, unit_price, discount and tax rate. The DATABASE
-- computes subtotal, tax and total, so a line with wrong arithmetic cannot exist.
-- Tax is charged on the amount AFTER discount.
CREATE TABLE invoice_lines (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  invoice_id      BIGINT NOT NULL REFERENCES invoices (id) ON DELETE CASCADE,
  product_id      BIGINT REFERENCES products (id),      -- for "revenue by product" reports
  description     TEXT    NOT NULL,
  quantity        INTEGER NOT NULL CHECK (quantity > 0),
  unit_price      BIGINT  NOT NULL CHECK (unit_price >= 0),
  discount_amount BIGINT  NOT NULL DEFAULT 0,
  tax_name        TEXT    NOT NULL,
  tax_rate_bps    INTEGER NOT NULL CHECK (tax_rate_bps BETWEEN 0 AND 10000),
  line_subtotal   BIGINT GENERATED ALWAYS AS (quantity::BIGINT * unit_price) STORED,
  tax_amount      BIGINT GENERATED ALWAYS AS
                    (((quantity::BIGINT * unit_price - discount_amount) * tax_rate_bps + 5000) / 10000) STORED,
  line_total      BIGINT GENERATED ALWAYS AS
                    ((quantity::BIGINT * unit_price - discount_amount)
                     + (((quantity::BIGINT * unit_price - discount_amount) * tax_rate_bps + 5000) / 10000)) STORED,
  CONSTRAINT line_discount_in_range
    CHECK (discount_amount >= 0 AND discount_amount <= quantity::BIGINT * unit_price)
);

-- Payments are an append-only ledger. A mistake is corrected by a new entry,
-- never by editing history (enforced by trigger).
CREATE TABLE payments (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  invoice_id  BIGINT NOT NULL REFERENCES invoices (id),
  method      payment_method_t NOT NULL,
  amount      BIGINT NOT NULL CHECK (amount > 0),
  paid_on     DATE   NOT NULL,
  reference   TEXT,                                     -- UPI ref / cheque no. / txn id
  note        TEXT,
  recorded_by BIGINT REFERENCES users (id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per discount applied to an invoice. The UNIQUE pair means the same
-- discount can never be counted twice for the same invoice, even on a re-run.
CREATE TABLE discount_redemptions (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  discount_id BIGINT NOT NULL REFERENCES discounts (id),
  invoice_id  BIGINT NOT NULL REFERENCES invoices (id),
  amount      BIGINT NOT NULL CHECK (amount > 0),
  redeemed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT one_redemption_per_invoice UNIQUE (discount_id, invoice_id)
);


-- =============================================================================
-- 5. SYSTEM: AUDIT LOG
-- =============================================================================

-- "Who changed the tax rate, and what was it before?" Filled by a trigger on
-- the admin-configured tables. old_data / new_data are full JSON snapshots.
CREATE TABLE audit_log (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  table_name TEXT   NOT NULL,
  row_id     BIGINT NOT NULL,
  action     TEXT   NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
  old_data   JSONB,
  new_data   JSONB,
  changed_by BIGINT REFERENCES users (id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================================================
-- 6. TRIGGERS  --  rules the database enforces even if the app has a bug
--
-- A trigger is a function Postgres runs automatically around INSERT/UPDATE/
-- DELETE. Errors raised here use Postgres code P0001; the messages are written
-- for humans so the API can show them as-is.
-- =============================================================================

-- ---- 6.1 Keep updated_at fresh ---------------------------------------------
CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['users', 'customers', 'products', 'plans', 'discounts',
                           'quotation_templates', 'subscriptions', 'invoices']
  LOOP
    EXECUTE format(
      'CREATE TRIGGER trg_%s_updated BEFORE UPDATE ON %I
         FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t, t);
  END LOOP;
END $$;

-- ---- 6.2 State machines (read from status_transitions) ---------------------
-- TG_ARGV[0] is the entity name passed in CREATE TRIGGER below.
CREATE FUNCTION enforce_status_flow() RETURNS trigger AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT EXISTS (
       SELECT 1 FROM status_transitions
       WHERE entity      = TG_ARGV[0]
         AND from_status = OLD.status::TEXT
         AND to_status   = NEW.status::TEXT)
  THEN
    RAISE EXCEPTION 'Invalid % status change: % -> %',
      lower(TG_ARGV[0]), OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_flow BEFORE UPDATE OF status ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION enforce_status_flow('SUBSCRIPTION');
CREATE TRIGGER trg_invoices_flow BEFORE UPDATE OF status ON invoices
  FOR EACH ROW EXECUTE FUNCTION enforce_status_flow('INVOICE');

-- Everything starts life as DRAFT. Without this, a row could be INSERTED
-- straight into PAID and skip the whole state machine.
CREATE FUNCTION require_draft_on_insert() RETURNS trigger AS $$
BEGIN
  IF NEW.status <> 'DRAFT' THEN
    RAISE EXCEPTION '% must be created as DRAFT (got %)', TG_TABLE_NAME, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_draft BEFORE INSERT ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION require_draft_on_insert();
CREATE TRIGGER trg_invoices_draft BEFORE INSERT ON invoices
  FOR EACH ROW EXECUTE FUNCTION require_draft_on_insert();

-- ---- 6.3 Plan rules: pause / early close / renew ---------------------------
CREATE FUNCTION enforce_subscription_plan_rules() RETURNS trigger AS $$
DECLARE
  v_plan  plans%ROWTYPE;
  v_today DATE;
BEGIN
  SELECT * INTO v_plan FROM plans WHERE id = NEW.plan_id;
  SELECT today INTO v_today FROM app_clock;

  IF NEW.status IS DISTINCT FROM OLD.status THEN
    IF NEW.status = 'PAUSED' AND NOT v_plan.allow_pause THEN
      RAISE EXCEPTION 'Plan "%" does not allow pausing', v_plan.name;
    END IF;
    IF NEW.status = 'CLOSED'
       AND OLD.status IN ('CONFIRMED', 'ACTIVE', 'PAUSED')
       AND NEW.expiry_date > v_today
       AND NOT v_plan.allow_early_close THEN
      RAISE EXCEPTION 'Plan "%" cannot be closed before its expiry date (%)',
        v_plan.name, NEW.expiry_date;
    END IF;
  END IF;

  -- Renewal = pushing the expiry date out on a live subscription.
  IF NEW.expiry_date > OLD.expiry_date
     AND OLD.status IN ('ACTIVE', 'PAUSED')
     AND NOT v_plan.allow_renew THEN
    RAISE EXCEPTION 'Plan "%" does not allow renewal', v_plan.name;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_plan_rules BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION enforce_subscription_plan_rules();

-- ---- 6.4 Subscription history ----------------------------------------------
-- The app sets the acting user per transaction with:
--   SELECT set_config('app.user_id', '<id>', true);
-- current_setting(..., true) returns NULL if it was never set.
CREATE FUNCTION log_subscription_event() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO subscription_events (subscription_id, from_status, to_status, changed_by)
    VALUES (NEW.id, NULL, NEW.status,
            NULLIF(current_setting('app.user_id', true), '')::BIGINT);
  ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
    INSERT INTO subscription_events (subscription_id, from_status, to_status, changed_by)
    VALUES (NEW.id, OLD.status, NEW.status,
            NULLIF(current_setting('app.user_id', true), '')::BIGINT);
  END IF;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_events AFTER INSERT OR UPDATE OF status ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION log_subscription_event();

-- ---- 6.5 Invoice integrity -------------------------------------------------
-- Header totals are always the sum of the lines. Fires after every line change.
CREATE FUNCTION rollup_invoice_totals() RETURNS trigger AS $$
DECLARE
  v_invoice_id BIGINT;
BEGIN
  IF TG_OP = 'DELETE' THEN v_invoice_id := OLD.invoice_id;
  ELSE                     v_invoice_id := NEW.invoice_id;
  END IF;

  UPDATE invoices i
     SET subtotal       = s.sub,
         discount_total = s.disc,
         tax_total      = s.tax,
         total          = s.sub - s.disc + s.tax
    FROM (SELECT COALESCE(SUM(line_subtotal),   0) AS sub,
                 COALESCE(SUM(discount_amount), 0) AS disc,
                 COALESCE(SUM(tax_amount),      0) AS tax
            FROM invoice_lines
           WHERE invoice_id = v_invoice_id) s
   WHERE i.id = v_invoice_id;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoice_lines_rollup AFTER INSERT OR UPDATE OR DELETE ON invoice_lines
  FOR EACH ROW EXECUTE FUNCTION rollup_invoice_totals();

-- Lines can only change while the invoice is still a DRAFT.
CREATE FUNCTION lock_invoice_lines() RETURNS trigger AS $$
DECLARE
  v_invoice_id BIGINT;
  v_status     invoice_status_t;
BEGIN
  IF TG_OP = 'DELETE' THEN v_invoice_id := OLD.invoice_id;
  ELSE                     v_invoice_id := NEW.invoice_id;
  END IF;

  SELECT status INTO v_status FROM invoices WHERE id = v_invoice_id;
  IF v_status IS NOT NULL AND v_status <> 'DRAFT' THEN
    RAISE EXCEPTION 'Invoice lines can only change while the invoice is DRAFT (it is %)', v_status;
  END IF;

  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoice_lines_lock BEFORE INSERT OR UPDATE OR DELETE ON invoice_lines
  FOR EACH ROW EXECUTE FUNCTION lock_invoice_lines();

-- Once confirmed, an invoice's identity and amounts are frozen.
-- (amount_paid and status are allowed to move: that is how payments work.)
CREATE FUNCTION lock_confirmed_invoice() RETURNS trigger AS $$
BEGIN
  IF OLD.status <> 'DRAFT'
     AND ROW(NEW.subscription_id, NEW.customer_id, NEW.period_start, NEW.period_end,
             NEW.subtotal, NEW.discount_total, NEW.tax_total, NEW.total)
         IS DISTINCT FROM
         ROW(OLD.subscription_id, OLD.customer_id, OLD.period_start, OLD.period_end,
             OLD.subtotal, OLD.discount_total, OLD.tax_total, OLD.total)
  THEN
    RAISE EXCEPTION 'Invoice % is %: its amounts can no longer be changed', OLD.number, OLD.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoices_lock BEFORE UPDATE ON invoices
  FOR EACH ROW EXECUTE FUNCTION lock_confirmed_invoice();

-- ---- 6.6 Payments ----------------------------------------------------------
-- Before insert: invoice must be CONFIRMED and the payment must not exceed
-- the balance. FOR UPDATE locks the invoice row, so two simultaneous
-- payments queue up instead of both reading the same balance.
CREATE FUNCTION payments_guard() RETURNS trigger AS $$
DECLARE
  v_status  invoice_status_t;
  v_balance BIGINT;
BEGIN
  SELECT status, total - amount_paid
    INTO v_status, v_balance
    FROM invoices
   WHERE id = NEW.invoice_id
     FOR UPDATE;

  IF v_status <> 'CONFIRMED' THEN
    RAISE EXCEPTION 'Payments can only be recorded on CONFIRMED invoices (this one is %)', v_status;
  END IF;
  IF NEW.amount > v_balance THEN
    RAISE EXCEPTION 'Payment of % paise is more than the outstanding balance of % paise',
      NEW.amount, v_balance;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_guard BEFORE INSERT ON payments
  FOR EACH ROW EXECUTE FUNCTION payments_guard();

-- After insert: add to amount_paid, and flip to PAID when fully paid.
-- In an UPDATE, the right-hand side sees the OLD row values.
CREATE FUNCTION payments_apply() RETURNS trigger AS $$
BEGIN
  UPDATE invoices
     SET amount_paid = amount_paid + NEW.amount,
         status      = CASE WHEN amount_paid + NEW.amount = total
                            THEN 'PAID'::invoice_status_t
                            ELSE status END
   WHERE id = NEW.invoice_id;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_apply AFTER INSERT ON payments
  FOR EACH ROW EXECUTE FUNCTION payments_apply();

-- ---- 6.7 Append-only tables ------------------------------------------------
CREATE FUNCTION forbid_change() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_append_only BEFORE UPDATE OR DELETE ON payments
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER trg_audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION forbid_change();

-- ---- 6.8 Discount usage ----------------------------------------------------
-- Inserting a redemption bumps times_used. The UPDATE takes a row lock, so
-- concurrent redemptions queue up, and CHECK discount_within_limit rejects
-- the one that would exceed the limit.
CREATE FUNCTION bump_discount_usage() RETURNS trigger AS $$
BEGIN
  UPDATE discounts SET times_used = times_used + 1 WHERE id = NEW.discount_id;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_redemptions_bump AFTER INSERT ON discount_redemptions
  FOR EACH ROW EXECUTE FUNCTION bump_discount_usage();

-- ---- 6.9 Audit trail for admin-configured tables ---------------------------
CREATE FUNCTION audit_row() RETURNS trigger AS $$
DECLARE
  v_old JSONB;
  v_new JSONB;
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') THEN v_old := to_jsonb(OLD); END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN v_new := to_jsonb(NEW); END IF;

  INSERT INTO audit_log (table_name, row_id, action, old_data, new_data, changed_by)
  VALUES (TG_TABLE_NAME,
          COALESCE(v_new ->> 'id', v_old ->> 'id')::BIGINT,
          TG_OP, v_old, v_new,
          NULLIF(current_setting('app.user_id', true), '')::BIGINT);
  RETURN NULL;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['taxes', 'products', 'plans', 'discounts']
  LOOP
    EXECUTE format(
      'CREATE TRIGGER trg_%s_audit AFTER INSERT OR UPDATE OR DELETE ON %I
         FOR EACH ROW EXECUTE FUNCTION audit_row()', t, t);
  END LOOP;
END $$;

-- ---- 6.10 Real-time: tell the app something changed ------------------------
-- The API holds one connection running LISTEN billing_events and pushes each
-- message to open browsers over Server-Sent Events. (Identical messages inside
-- one transaction are merged by Postgres; the frontend should also debounce.)
CREATE FUNCTION notify_billing_event() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('billing_events',
    json_build_object('table', TG_TABLE_NAME, 'op', TG_OP, 'id', NEW.id)::TEXT);
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoices_notify AFTER INSERT OR UPDATE OF status ON invoices
  FOR EACH ROW EXECUTE FUNCTION notify_billing_event();
CREATE TRIGGER trg_payments_notify AFTER INSERT ON payments
  FOR EACH ROW EXECUTE FUNCTION notify_billing_event();
CREATE TRIGGER trg_subscriptions_notify AFTER INSERT OR UPDATE OF status ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION notify_billing_event();


-- =============================================================================
-- 7. INDEXES
-- Postgres indexes PRIMARY KEY and UNIQUE columns automatically, but NOT
-- foreign keys. Index the ones you filter or join on.
-- =============================================================================

-- Fast "company contains 'tech'" search (ILIKE '%tech%')
CREATE INDEX idx_customers_company_trgm ON customers USING gin (company_name gin_trgm_ops);

CREATE INDEX idx_products_tax              ON products (tax_id);
CREATE INDEX idx_variants_product          ON product_variants (product_id);
CREATE INDEX idx_discounts_live            ON discounts (start_date, end_date) WHERE is_active;
CREATE INDEX idx_qtl_template              ON quotation_template_lines (template_id);

CREATE INDEX idx_subscriptions_customer    ON subscriptions (customer_id);
CREATE INDEX idx_subscriptions_plan        ON subscriptions (plan_id);
CREATE INDEX idx_subscriptions_status      ON subscriptions (status);
-- PARTIAL index: billing day only looks at ACTIVE subscriptions, so only
-- those are indexed. It stays tiny however many closed ones pile up.
CREATE INDEX idx_subscriptions_due         ON subscriptions (next_billing_date) WHERE status = 'ACTIVE';
CREATE INDEX idx_sub_lines_subscription    ON subscription_lines (subscription_id);
CREATE INDEX idx_sub_lines_product         ON subscription_lines (product_id);
CREATE INDEX idx_sub_discounts_discount    ON subscription_discounts (discount_id);
CREATE INDEX idx_sub_events_subscription   ON subscription_events (subscription_id, changed_at);

CREATE INDEX idx_invoices_customer         ON invoices (customer_id, issue_date DESC);
CREATE INDEX idx_invoices_status           ON invoices (status);
-- PARTIAL index for the overdue / outstanding queries.
CREATE INDEX idx_invoices_open             ON invoices (due_date) WHERE status = 'CONFIRMED';
CREATE INDEX idx_invoice_lines_invoice     ON invoice_lines (invoice_id);
CREATE INDEX idx_invoice_lines_product     ON invoice_lines (product_id);
CREATE INDEX idx_payments_invoice          ON payments (invoice_id);
CREATE INDEX idx_payments_paid_on          ON payments (paid_on);
CREATE INDEX idx_redemptions_invoice       ON discount_redemptions (invoice_id);
CREATE INDEX idx_audit_row                 ON audit_log (table_name, row_id);
CREATE INDEX idx_pw_resets_user            ON password_resets (user_id);


-- =============================================================================
-- 8. VIEWS
-- Computed facts live here, never in stored columns, so they can't go stale.
-- Every view reads "today" from app_clock, so the Time Machine moves them.
-- =============================================================================

-- One row per invoice with its balance and overdue flag.
CREATE VIEW v_invoice_summary AS
SELECT i.*,
       c.company_name,
       (i.total - i.amount_paid) AS balance,
       (i.status = 'CONFIRMED' AND i.due_date < k.today AND i.amount_paid < i.total) AS is_overdue,
       CASE WHEN i.status = 'CONFIRMED' AND i.due_date < k.today AND i.amount_paid < i.total
            THEN k.today - i.due_date
            ELSE 0 END AS days_past_due
  FROM invoices i
  JOIN customers c ON c.id = i.customer_id
 CROSS JOIN app_clock k;

CREATE VIEW v_overdue_invoices AS
SELECT * FROM v_invoice_summary WHERE is_overdue;

-- Monthly recurring revenue per ACTIVE subscription (before tax and discounts),
-- normalised to a month: weekly x 52/12, yearly / 12, daily x 365/12.
CREATE VIEW v_subscription_mrr AS
SELECT s.id AS subscription_id,
       s.customer_id,
       s.plan_id,
       p.billing_period,
       COALESCE(SUM(l.line_subtotal), 0) AS recurring_amount,
       ROUND(COALESCE(SUM(l.line_subtotal), 0) *
             CASE p.billing_period
               WHEN 'DAILY'   THEN 365.0 / 12
               WHEN 'WEEKLY'  THEN  52.0 / 12
               WHEN 'MONTHLY' THEN   1.0
               WHEN 'YEARLY'  THEN   1.0 / 12
             END)::BIGINT AS mrr
  FROM subscriptions s
  JOIN plans p ON p.id = s.plan_id
  LEFT JOIN subscription_lines l ON l.subscription_id = s.id
 WHERE s.status = 'ACTIVE'
 GROUP BY s.id, p.billing_period;

CREATE VIEW v_monthly_collections AS
SELECT date_trunc('month', paid_on)::DATE AS month,
       SUM(amount)::BIGINT                AS collected,
       COUNT(*)                           AS payment_count
  FROM payments
 GROUP BY 1
 ORDER BY 1;

-- The finance lead's "one place": a single row of headline numbers.
CREATE VIEW v_dashboard_kpis AS
SELECT
  (SELECT COUNT(*) FROM subscriptions WHERE status = 'ACTIVE')                       AS active_subscriptions,
  (SELECT COALESCE(SUM(mrr), 0)::BIGINT FROM v_subscription_mrr)                     AS mrr,
  (SELECT COALESCE(SUM(p.amount), 0)::BIGINT FROM payments p
    WHERE p.paid_on >= date_trunc('month', k.today)::DATE AND p.paid_on <= k.today)  AS collected_this_month,
  (SELECT COALESCE(SUM(total - amount_paid), 0)::BIGINT FROM invoices
    WHERE status = 'CONFIRMED')                                                      AS outstanding,
  (SELECT COUNT(*) FROM v_invoice_summary WHERE is_overdue)                          AS overdue_invoices,
  (SELECT COALESCE(SUM(balance), 0)::BIGINT FROM v_invoice_summary WHERE is_overdue) AS overdue_amount,
  k.today                                                                            AS as_of
  FROM app_clock k;


-- =============================================================================
-- NOTES FOR THE APP LAYER (rules a CHECK constraint cannot express)
-- =============================================================================
--  * Start of every write transaction:  SELECT set_config('app.user_id', '<id>', true);
--    so history and audit rows record WHO did it.
--  * Billing insert:  INSERT INTO invoices (...) ON CONFLICT (subscription_id, period_start)
--    DO NOTHING RETURNING id;   -> no row back means "already billed, skip".
--  * Service layer checks (they need to look at other tables):
--      - subscription.start_date falls inside the plan's availability window
--      - every product line quantity >= plan.min_quantity
--      - payment.paid_on is not in the future (compare to app_clock.today)
--      - discount eligibility at billing time: dates, min_purchase, min_quantity
--  * Error mapping:  P0001 -> show the message as written; 23505 unique,
--    23503 foreign key, 23514 check -> map by constraint name to a friendly sentence.
-- =============================================================================