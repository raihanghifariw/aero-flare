"""
Integration tests for Tiles API (GET /api/v1/tiles/{event_id}).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent


@pytest.mark.asyncio
async def test_get_tile_not_found(client: AsyncClient) -> None:
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/tiles/{random_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_tile_success_redirect(client: AsyncClient, db_session: AsyncSession) -> None:
    event = FireEvent(
        id=uuid.uuid4(),
        firms_id="firms_t1",
        detected_at=datetime.now(timezone.utc),
        lat=-2.0,
        lon=112.0,
        frp=50.0,
        brightness=320.0,
        satellite="NOAA-20",
        tile_url="tiles/sample.png",
        status="TRIAGED",
    )
    db_session.add(event)
    await db_session.flush()

    with patch("app.api.v1.tiles.get_r2_presigned_url", return_value="https://r2.example.com/tiles/sample.png"):
        response = await client.get(f"/api/v1/tiles/{event.id}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://r2.example.com/tiles/sample.png"
