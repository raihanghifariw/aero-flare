"""
Alembic environment configuration for async SQLAlchemy.
Reads DATABASE_URL from environment variable / .env file.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

# Add the backend/ directory to sys.path so `from app.models import ...` works
# regardless of which directory alembic is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Load .env from backend/../.env (root of aero-flare/) so DATABASE_URL is available
_dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_dotenv_path, override=False)
# Also try the current working directory .env as fallback
load_dotenv(override=False)

# Alembic Config object
config = context.config

# Override version_locations using an absolute Path so paths containing
# spaces (e.g. "Project Space IBM") are not split into multiple tokens.
_versions_dir = str(Path(__file__).resolve().parent / "versions")
config.set_main_option("version_locations", _versions_dir)

# Resolve DATABASE_URL and ensure it uses the asyncpg driver.
# Alembic env.py may be run from any directory; we normalise the URL here
# so async_engine creation never accidentally loads the sync psycopg2 driver.
_raw_url = os.environ.get("DATABASE_URL", "")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Copy .env.example → .env and fill in the Supabase connection string."
    )

# Guarantee async driver: replace postgresql:// or postgresql+psycopg2:// with asyncpg
if _raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://"):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
elif _raw_url.startswith("postgresql+psycopg2://"):
    _async_url = _raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
else:
    _async_url = _raw_url  # already correct (e.g. postgresql+asyncpg://)

# Set both forms so offline mode (which uses the config url directly) also works
config.set_main_option("sqlalchemy.url", _async_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so autogenerate detects them
from app.models import base  # noqa: F401, E402
from app.models import fire_event  # noqa: F401, E402
from app.models import triage_report  # noqa: F401, E402
from app.models import prediction  # noqa: F401, E402
from app.models import webhook  # noqa: F401, E402
from app.models import audit_log  # noqa: F401, E402

target_metadata = base.Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — no DB connection needed."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async DB connection.

    We build the engine directly from _async_url (already validated to use
    asyncpg) rather than through async_engine_from_config, which can
    accidentally pick up the sync psycopg2 driver when the URL in the config
    section doesn't carry an explicit +asyncpg suffix.

    statement_cache_size=0 is required when connecting via Supabase pooler
    (pgbouncer transaction/statement mode) — without it asyncpg reuses
    prepared statement names across pooled connections and raises
    DuplicatePreparedStatementError.
    """
    connectable = create_async_engine(
        _async_url,
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
