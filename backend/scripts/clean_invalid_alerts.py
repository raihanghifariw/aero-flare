"""
Clean up invalid ALERTED events in Supabase PostgreSQL.
Demotes low-FRP (<30MW), low-danger (Level 1-2), and False Positive/Industrial events
from status='ALERTED' to status='TRIAGED'.

Run from backend/ directory:
    python scripts/clean_invalid_alerts.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
url = re.sub(r"^postgres://", "postgresql+asyncpg://", url)

print(f"Target DB: {re.sub(r':([^:@]+)@', ':***@', url)}\n")

# Demote invalid ALERTED statuses to TRIAGED:
#  1. Classification is FALSE_POSITIVE or INDUSTRIAL_SOURCE
#  2. Danger level is < 3
#  3. FRP is < 30.0 MW (unless Level 4/5 CONFIRMED_FIRE)
DEMOTE_SQL = """
UPDATE fire_events
SET status = 'TRIAGED'
FROM triage_reports
WHERE fire_events.id = triage_reports.event_id
  AND fire_events.status = 'ALERTED'
  AND (
    triage_reports.classification IN ('FALSE_POSITIVE', 'INDUSTRIAL_SOURCE')
    OR triage_reports.danger_level < 3
    OR (fire_events.frp < 30.0 AND triage_reports.danger_level < 4)
  );
"""

SELECT_ALERTED_STATS = """
SELECT 
    fe.status,
    tr.classification,
    tr.danger_level,
    COUNT(*) as count
FROM fire_events fe
LEFT JOIN triage_reports tr ON fe.id = tr.event_id
WHERE fe.status = 'ALERTED'
GROUP BY fe.status, tr.classification, tr.danger_level
ORDER BY tr.danger_level DESC, count DESC;
"""

async def main() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    async with engine.connect() as conn:
        rows_before = await conn.execute(text(SELECT_ALERTED_STATS))
        print("ALERTED Events Breakdown BEFORE Cleanup:")
        for r in rows_before.fetchall():
            print(f"  - Classification: {r[1]}, Danger Level: {r[2]} -> Count: {r[3]}")

    async with engine.begin() as conn:
        res = await conn.execute(text(DEMOTE_SQL))
        print(f"\nCleaned & Demoted Invalid ALERTED Rows: {res.rowcount}")

    async with engine.connect() as conn:
        rows_after = await conn.execute(text(SELECT_ALERTED_STATS))
        print("\nALERTED Events Breakdown AFTER Cleanup:")
        for r in rows_after.fetchall():
            print(f"  - Classification: {r[1]}, Danger Level: {r[2]} -> Count: {r[3]}")

    await engine.dispose()
    print("\nDatabase cleanup completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
