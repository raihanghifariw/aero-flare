"""
pytest configuration and shared fixtures for all Aero-Flare backend tests.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Patch the API_KEY env var BEFORE app imports so Settings loads the test value.
# This avoids the "field required" ValidationError when API_KEY is not set in CI.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("CLOUDFLARE_R2_ACCOUNT_ID", "test-account-id")
os.environ.setdefault("CLOUDFLARE_R2_ACCESS_KEY", "test-access-key")
os.environ.setdefault("CLOUDFLARE_R2_SECRET", "test-secret")
os.environ.setdefault("FIRMS_API_KEY", "test-firms-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")
os.environ.setdefault("TELEGRAM_CHANNEL_ID", "-100123456789")

from app.api.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402 — must be after env patching
from app.models.base import Base  # noqa: E402

# ─── In-memory SQLite test engine ────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Create all tables, yield a session, then drop all tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """
    AsyncClient wired to the test app.
    - DB dependency overridden to use in-memory SQLite session.
    - X-API-Key header pre-set to the test value in os.environ["API_KEY"].
    """
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": os.environ["API_KEY"]},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_ollama(mocker):  # type: ignore[no-untyped-def]
    """Mock the VLM HTTP call so tests never hit a real Ollama instance."""
    return mocker.patch(
        "app.services.triage.vlm_client.call_vlm",
        new_callable=AsyncMock,
    )


@pytest.fixture
def mock_telegram(mocker):  # type: ignore[no-untyped-def]
    """Mock Telegram send so tests never dispatch real messages."""
    return mocker.patch(
        "app.services.alerts.telegram_service.send_alert",
        new_callable=AsyncMock,
    )


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the test session (pytest-asyncio requirement)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
