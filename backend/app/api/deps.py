"""
FastAPI dependency injection helpers.
Used with Depends() in all route handlers.

`verify_api_key` is re-exported from app.core.security for backwards-
compatibility with any existing imports in routers.
"""
from __future__ import annotations

from typing import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_api_key  # canonical implementation  # noqa: F401
from app.models.base import AsyncSessionLocal

logger = structlog.get_logger()


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yields an async DB session per request. Closes after request completes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
