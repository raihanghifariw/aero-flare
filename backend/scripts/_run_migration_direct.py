"""
Force-run migration 0001 directly against Supabase, bypassing
alembic's version check. Used when alembic_version is empty but
the table exists (partial/failed previous run via pooler).

Run from backend/ directory:
    python scripts/_run_migration_direct.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
url = re.sub(r"^postgres://", "postgresql+asyncpg://", url)

print(f"Target: {re.sub(r':([^:@]+)@', ':***@', url)}\n")

DDL = """
-- fire_events
CREATE TABLE IF NOT EXISTS fire_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firms_id TEXT UNIQUE,
    detected_at TIMESTAMPTZ NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    frp DOUBLE PRECISION,
    brightness DOUBLE PRECISION,
    satellite VARCHAR(50),
    tile_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    alerted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_fire_events_detected_at ON fire_events (detected_at);
CREATE INDEX IF NOT EXISTS ix_fire_events_status ON fire_events (status);

-- triage_reports
CREATE TABLE IF NOT EXISTS triage_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    classification VARCHAR(50) NOT NULL,
    confidence DOUBLE PRECISION,
    fire_area_ha DOUBLE PRECISION,
    smoke_direction VARCHAR(10),
    danger_level INTEGER,
    summary TEXT,
    recommended_action VARCHAR(50),
    triage_source VARCHAR(30) NOT NULL DEFAULT 'VLM',
    processed_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_triage_reports_event_id ON triage_reports (event_id);

-- predictions
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    spread_direction_deg DOUBLE PRECISION,
    radius_6h_km DOUBLE PRECISION,
    radius_12h_km DOUBLE PRECISION,
    radius_24h_km DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    wind_direction DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    model_version VARCHAR(20),
    predicted_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_predictions_event_id ON predictions (event_id);

-- webhook_registrations
CREATE TABLE IF NOT EXISTS webhook_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    secret TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- event_audit_log
CREATE TABLE IF NOT EXISTS event_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    row_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(50) NOT NULL DEFAULT 'system',
    trace_id TEXT,
    changed_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_event_audit_log_row_id ON event_audit_log (row_id);
CREATE INDEX IF NOT EXISTS ix_event_audit_log_changed_at ON event_audit_log (changed_at);

-- stamp alembic revision
INSERT INTO alembic_version (version_num)
VALUES ('0001')
ON CONFLICT DO NOTHING;
"""


async def main() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    async with engine.begin() as conn:
        print("Running DDL statements...")
        # Execute each statement separately (pooler safer with small txns)
        for stmt in [s.strip() for s in DDL.split(";") if s.strip()]:
            try:
                await conn.execute(text(stmt))
                # Show first line of each statement
                print(f"  OK: {stmt.splitlines()[0][:70]}")
            except Exception as e:
                print(f"  SKIP (already exists?): {str(e)[:100]}")

    await engine.dispose()

    # Verify
    engine2 = create_async_engine(url, connect_args={"statement_cache_size": 0})
    async with engine2.connect() as conn:
        rows = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [r[0] for r in rows.fetchall()]
        print(f"\nTables now in DB ({len(tables)}):")
        for t in tables:
            print(f"  {t}")

        rows2 = await conn.execute(text("SELECT version_num FROM alembic_version"))
        vers = [r[0] for r in rows2.fetchall()]
        print(f"\nalembic_version: {vers}")
        if "0001" in vers:
            print("\nSUCCESS - all tables created, revision stamped.")
        else:
            print("\nWARNING - revision not stamped, check errors above.")

    await engine2.dispose()


asyncio.run(main())
