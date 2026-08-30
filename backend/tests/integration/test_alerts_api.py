"""
Integration tests for Alerts API (POST /api/v1/alerts/retry/{event_id}).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent


def _make_event(**kwargs) -> FireEvent:
    defaults = dict(
        id=uuid.uuid4(),
        firms_id=f"firms_{uuid.uuid4().hex[:8]}",
        detected_at=datetime.now(timezone.utc),
        lat=-2.345,
        lon=112.456,
        frp=55.2,
        brightness=320.5,
        satellite="NOAA-20",
        tile_url=None,
        status="ALERTED_FAILED",
        alerted_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return FireEvent(**defaults)


@pytest.mark.asyncio
async def test_retry_alert_success(client: AsyncClient, db_session: AsyncSession) -> None:
    event = _make_event(status="ALERTED_FAILED")
    db_session.add(event)
    await db_session.flush()

    response = await client.post(f"/api/v1/alerts/retry/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.id)
    assert "queued" in data["message"]


@pytest.mark.asyncio
async def test_retry_alert_not_found(client: AsyncClient) -> None:
    random_id = uuid.uuid4()
    response = await client.post(f"/api/v1/alerts/retry/{random_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_alert_invalid_status(client: AsyncClient, db_session: AsyncSession) -> None:
    event = _make_event(status="PREDICTED")
    db_session.add(event)
    await db_session.flush()

    response = await client.post(f"/api/v1/alerts/retry/{event.id}")
    assert response.status_code == 400
    data = response.json()
    assert "INVALID_STATUS" in str(data)
