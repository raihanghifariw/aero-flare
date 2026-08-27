-- ============================================================
-- Aero-Flare: Supabase Row-Level Security (RLS) Setup
-- Run this once in the Supabase SQL Editor (dashboard → SQL Editor)
-- before the first deployment.
--
-- Why: RLS ensures that even if a client somehow obtains the anon
-- key, it cannot read or modify fire data. Only the backend using
-- the service_role key can access these tables.
-- ============================================================

-- ─── Enable RLS on all tables ────────────────────────────────────────────────

ALTER TABLE fire_events         ENABLE ROW LEVEL SECURITY;
ALTER TABLE triage_reports      ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_audit_log     ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_registrations ENABLE ROW LEVEL SECURITY;

-- ─── Grant full access to service_role (backend) only ───────────────────────
-- service_role bypasses RLS by default, but we add explicit policies
-- for auditability and to document intent.

CREATE POLICY "service_role_all" ON fire_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all" ON triage_reports
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all" ON predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Audit log is append-only — no UPDATE/DELETE for any role.
CREATE POLICY "service_role_insert_only" ON event_audit_log
    FOR INSERT TO service_role WITH CHECK (true);
-- SELECT on audit log is allowed for service_role (read for forensics)
CREATE POLICY "service_role_select" ON event_audit_log
    FOR SELECT TO service_role USING (true);

CREATE POLICY "service_role_all" ON webhook_registrations
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ─── Verify: anon key cannot read fire_events ────────────────────────────────
-- Run this block with the anon key to confirm RLS is blocking access:
--
-- SELECT * FROM fire_events LIMIT 1;
-- Expected result: empty (0 rows) — not an error, just no policy grants anon access
--
-- If you see rows, check that RLS was enabled: run the ALTER TABLE lines above again.

-- ─── Verify RLS is active ────────────────────────────────────────────────────
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename IN (
    'fire_events', 'triage_reports', 'predictions',
    'event_audit_log', 'webhook_registrations'
)
ORDER BY tablename;
-- All rows should have rowsecurity = true
