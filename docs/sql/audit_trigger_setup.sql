-- ============================================================
-- Aero-Flare: PostgreSQL Audit Trigger Setup
-- Run this ONCE in Supabase SQL Editor after running migrations.
-- Creates the event_audit_log table and triggers on all 3 core tables.
--
-- Implements ADR-013: Immutable Audit Trail via PostgreSQL Triggers
-- ============================================================

-- ─── 1. Create audit log table ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS event_audit_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name      TEXT        NOT NULL,
    operation       TEXT        NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    row_id          UUID        NOT NULL,
    old_data        JSONB,                       -- NULL for INSERT
    new_data        JSONB,                       -- NULL for DELETE
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by      TEXT        DEFAULT current_user,
    trace_id        TEXT                         -- OpenTelemetry trace_id (set by app)
);

-- Index for forensic lookups by table + row
CREATE INDEX IF NOT EXISTS idx_audit_log_table_row ON event_audit_log (table_name, row_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON event_audit_log (changed_at DESC);

-- ─── 2. Create audit trigger function ────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO event_audit_log (table_name, operation, row_id, new_data)
        VALUES (TG_TABLE_NAME, 'INSERT', NEW.id, to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO event_audit_log (table_name, operation, row_id, old_data, new_data)
        VALUES (TG_TABLE_NAME, 'UPDATE', NEW.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO event_audit_log (table_name, operation, row_id, old_data)
        VALUES (TG_TABLE_NAME, 'DELETE', OLD.id, to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─── 3. Attach trigger to all three core tables ───────────────────────────────

DROP TRIGGER IF EXISTS trg_audit_fire_events    ON fire_events;
DROP TRIGGER IF EXISTS trg_audit_triage_reports ON triage_reports;
DROP TRIGGER IF EXISTS trg_audit_predictions    ON predictions;

CREATE TRIGGER trg_audit_fire_events
    AFTER INSERT OR UPDATE OR DELETE ON fire_events
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER trg_audit_triage_reports
    AFTER INSERT OR UPDATE OR DELETE ON triage_reports
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER trg_audit_predictions
    AFTER INSERT OR UPDATE OR DELETE ON predictions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

-- ─── 4. Verify triggers are attached ─────────────────────────────────────────
SELECT
    event_object_table  AS table_name,
    trigger_name,
    event_manipulation  AS event
FROM information_schema.triggers
WHERE event_object_table IN ('fire_events', 'triage_reports', 'predictions')
ORDER BY table_name, event_manipulation;
-- Expected: 9 rows (3 tables × 3 events: INSERT, UPDATE, DELETE)

-- ─── 5. Test audit trail is working ──────────────────────────────────────────
-- After inserting a test event:
-- SELECT COUNT(*) FROM event_audit_log WHERE table_name = 'fire_events';
-- Should return 1 (INSERT captured).
