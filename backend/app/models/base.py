"""
SQLAlchemy async engine + session factory.
pool_pre_ping=True is mandatory — prevents silent failures on stale connections (Railway/Supabase idle).

SQLite (used in tests) does not support pool_size / max_overflow — those kwargs are
skipped automatically when the URL scheme starts with "sqlite".

Engine is created lazily (on first access) so that importing this module during
alembic env.py or test collection does NOT immediately open a DB connection.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Module-level singletons — populated on first call to _get_engine().
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _make_engine() -> AsyncEngine:
    """Build and return a fresh AsyncEngine from current settings."""
    settings = get_settings()
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    kwargs: dict = {
        "echo": settings.ENVIRONMENT == "development",
    }

    if not is_sqlite:
        # SQLite does not support connection pool tuning; PostgreSQL does.
        # statement_cache_size=0 is required when connecting via Supabase
        # pooler (pgbouncer) — prevents DuplicatePreparedStatementError.
        kwargs.update(
            pool_pre_ping=True,  # MANDATORY — validates connection before use
            pool_size=settings.SQLALCHEMY_POOL_SIZE,
            max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
            pool_timeout=30,
            connect_args={"statement_cache_size": 0},
        )

    return create_async_engine(url, **kwargs)


def _get_engine() -> AsyncEngine:
    """Return the shared engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Public API — used by app startup, scripts, and tests
# ---------------------------------------------------------------------------

# Lazy property-style accessors so existing code that does
#   from app.models.base import engine, AsyncSessionLocal
# continues to work without change.

class _LazyEngine:
    """Proxy that creates the real engine on first attribute access."""

    def __getattr__(self, name: str):  # type: ignore[override]
        return getattr(_get_engine(), name)

    # Support `engine.begin()` / `engine.connect()` etc. directly
    def __repr__(self) -> str:
        return repr(_get_engine())


engine: AsyncEngine = _LazyEngine()  # type: ignore[assignment]


def AsyncSessionLocal() -> AsyncSession:  # noqa: N802 — mimics sessionmaker call API
    """
    Lazily create and return a new AsyncSession.

    Call sites use `async with AsyncSessionLocal() as session:` — identical to
    calling a sessionmaker instance. The factory (and engine) are created on
    first use, so importing this module never opens a DB connection.

    NOTE: This must call the factory (`_get_session_factory()()`), not merely
    reference it — binding the bare function here previously returned the
    sessionmaker instead of a session, causing `AttributeError: __aenter__`.
    """
    return _get_session_factory()()


@asynccontextmanager
async def async_session_factory() -> AsyncGenerator[AsyncSession, None]:
    """Context manager that yields a DB session and closes it after use."""
    async with _get_session_factory()() as session:
        yield session


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass
