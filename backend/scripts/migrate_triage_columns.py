"""
Add cloud_cover_percent and visually_obscured columns to triage_reports table in Supabase PostgreSQL.
Run from backend/ directory:
    python scripts/migrate_triage_columns.py
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

ALTER_DDL = [
    "ALTER TABLE triage_reports ADD COLUMN IF NOT EXISTS cloud_cover_percent DOUBLE PRECISION;",
    "ALTER TABLE triage_reports ADD COLUMN IF NOT EXISTS visually_obscured BOOLEAN;",
]

async def main() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    async with engine.begin() as conn:
        print("Adding cloud columns to triage_reports...")
        for stmt in ALTER_DDL:
            try:
                await conn.execute(text(stmt))
                print(f"  OK: {stmt}")
            except Exception as e:
                print(f"  ERR: {e}")

    await engine.dispose()

    # Verify columns
    engine2 = create_async_engine(url, connect_args={"statement_cache_size": 0})
    async with engine2.connect() as conn:
        rows = await conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'triage_reports' ORDER BY ordinal_position"
        ))
        cols = rows.fetchall()
        print("\nColumns in triage_reports table:")
        for c in cols:
            print(f"  - {c[0]} ({c[1]})")

    await engine2.dispose()
    print("\nDatabase migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
