"""
Integration tests for the Predictions API endpoint.
GET /api/v1/predictions/{event_id}

Covers: FR-08, FR-09, FR-10 (spread prediction fields and storage).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.models.prediction import Prediction

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_event(**kwargs) -> FireEvent:
    defaults = dict(
        id=uuid.uuid4(),
        firms_id=f"firms_{uuid.uuid4().hex[:8]}",
        detected_at=datetime.now(timezone.utc),
        lat=-2.345,
        lon=112.456,
        frp=85.0,
        brightness=340.0,
        satellite="NOAA-20",
        tile_url=None,
        status="PREDICTED",
        alerted_at=None,
    )
    defaults.update(kwargs)
    return FireEvent(**defaults)


def _make_prediction(event_id: uuid.UUID, **kwargs) -> Prediction:
    defaults = dict(
        id=uuid.uuid4(),
        event_id=event_id,
        spread_direction_deg=135.0,
        radius_6h_km=3.2,
        radius_12h_km=6.8,
        radius_24h_km=14.5,
        wind_speed=5.2,
        wind_direction=135.0,
        humidity=35.0,
        model_version="xgb-v1.0",
        predicted_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Prediction(**defaults)


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_prediction_without_api_key_returns_403(
    client: AsyncClient,
) -> None:
    # httpx merges request headers with client-level defaults, so to simulate
    # "no key" we must explicitly send an empty X-API-Key (falsy → rejected).
    response = await client.get(
        f"/api/v1/predictions/{uuid.uuid4()}", headers={"X-API-Key": ""}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_prediction_returns_all_spread_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Prediction response must include all 4 spread targets (FR-09)."""
    event = _make_event()
    pred = _make_prediction(event.id)
    db_session.add(event)
    db_session.add(pred)
    await db_session.flush()

    response = await client.get(f"/api/v1/predictions/{event.id}")
    assert response.status_code == 200
    data = response.json()

    # FR-09: All 4 outputs present
    assert "spread_direction_deg" in data
    assert "radius_6h_km" in data
    assert "radius_12h_km" in data
    assert "radius_24h_km" in data

    # Values must be positive (FR-09 acceptance criterion)
    assert data["radius_6h_km"] > 0
    assert data["radius_12h_km"] > 0
    assert data["radius_24h_km"] > 0
    assert 0.0 <= data["spread_direction_deg"] <= 360.0


@pytest.mark.asyncio
async def test_get_prediction_event_id_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Prediction must be linked to the correct event (FR-10)."""
    event = _make_event()
    pred = _make_prediction(event.id)
    db_session.add(event)
    db_session.add(pred)
    await db_session.flush()

    response = await client.get(f"/api/v1/predictions/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.id)
    assert data["model_version"] == "xgb-v1.0"


@pytest.mark.asyncio
async def test_get_prediction_for_nonexistent_event_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/predictions/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_prediction_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/predictions/not-a-uuid-at-all")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_prediction_includes_weather_features(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Response must include wind_speed, wind_direction, humidity (FR-08 features)."""
    event = _make_event()
    pred = _make_prediction(
        event.id,
        wind_speed=7.3,
        wind_direction=220.0,
        humidity=42.0,
    )
    db_session.add(event)
    db_session.add(pred)
    await db_session.flush()

    response = await client.get(f"/api/v1/predictions/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["wind_speed"] == pytest.approx(7.3)
    assert data["wind_direction"] == pytest.approx(220.0)
    assert data["humidity"] == pytest.approx(42.0)
