"""
Diagnostic: check what tables exist in Supabase and whether
alembic_version is present + what revision it holds.
Run from backend/ directory: python scripts/_check_db.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from aero-flare root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv()  # fallback: cwd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Normalise to asyncpg
url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
url = re.sub(r"^postgres://", "postgresql+asyncpg://", url)

print(f"Connecting to: {re.sub(r':([^:@]+)@', ':***@', url)}\n")


async def main() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    async with engine.connect() as conn:
        # 1. All tables in public schema
        rows = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [r[0] for r in rows.fetchall()]
        print("Tables in public schema:")
        if tables:
            for t in tables:
                print(f"  [OK] {t}")
        else:
            print("  (none - database is empty)")

        # 2. alembic_version content
        print()
        if "alembic_version" in tables:
            rows2 = await conn.execute(text("SELECT version_num FROM alembic_version"))
            vers = [r[0] for r in rows2.fetchall()]
            print(f"alembic_version: {vers}")
        else:
            print("alembic_version: table does NOT exist")
            print("  -> migration 0001 has NOT been applied yet")

    await engine.dispose()
    print("\nDiagnostic complete.")


asyncio.run(main())
