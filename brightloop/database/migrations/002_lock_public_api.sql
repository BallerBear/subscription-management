-- =============================================================================
-- 002_lock_public_api.sql  --  close Supabase's auto-generated public API
--
-- WHY: Supabase publishes everything in the "public" schema through a REST
-- API that anyone holding the project's public key can call. Our app never
-- uses that API (all access goes through FastAPI), so we shut it completely.
--
-- TWO LAYERS (either one alone would be enough; both is belt and braces):
--   1. Row-Level Security ON with NO policies = non-owner roles see zero rows.
--   2. REVOKE every privilege from the API roles (anon, authenticated).
--
-- OUR BACKEND IS UNAFFECTED: it connects as the "postgres" owner role, which
-- owns the tables and bypasses RLS.
--
-- SAFE TO RE-RUN. Run it again after adding any new migration that creates
-- tables, because it only covers tables that exist at the moment it runs.
--
-- Also switch off the Data API in the Supabase dashboard (Project Settings ->
-- API / Data API) if you can find the toggle. This file works either way.
-- =============================================================================

-- Layer 1: RLS on for every table in public
DO $$
DECLARE
  t RECORD;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;

-- Layer 2: take away every privilege from the API roles.
-- The IF EXISTS check keeps this file working on plain Postgres (e.g. a local
-- Docker fallback), where the roles anon / authenticated do not exist.
DO $$
DECLARE
  r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated']
  LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      -- existing objects (REVOKE ... ON ALL TABLES also covers views)
      EXECUTE format('REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', r);
      -- objects created in the future by this role
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I', r);
    END IF;
  END LOOP;
END $$;

-- HOW TO VERIFY (Supabase SQL editor):
--   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
--   -> rowsecurity should be true for every row.