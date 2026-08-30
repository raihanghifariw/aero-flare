"""
Unit tests for dependency helpers in app.api.deps.
"""
from __future__ import annotations

import pytest

from app.api.deps import get_db


@pytest.mark.asyncio
async def test_get_db_session_flow() -> None:
    """Test get_db yields session and cleans up."""
    gen = get_db()
    session = await gen.__anext__()
    assert session is not None
    # End generator normally
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
