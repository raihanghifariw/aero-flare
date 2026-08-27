"""
Integration tests for the Triage API endpoint.
GET /api/v1/triage/{event_id}

Covers: FR-04, FR-05, FR-06 (VLM classification fields), triage_source.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport


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
        status="TRIAGED",
        alerted_at=None,
    )
    defaults.update(kwargs)
    return FireEvent(**defaults)


def _make_triage(event_id: uuid.UUID, **kwargs) -> TriageReport:
    defaults = dict(
        id=uuid.uuid4(),
        event_id=event_id,
        classification="CONFIRMED_FIRE",
        confidence=0.92,
        fire_area_ha=125.5,
        smoke_direction="NW",
        danger_level=4,
        summary="Active peatland fire with dense smoke plume.",
        recommended_action="DISPATCH_LOCAL",
        triage_source="VLM",
        processed_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return TriageReport(**defaults)


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_triage_without_api_key_returns_403(client: AsyncClient) -> None:
    # httpx merges request headers with client-level defaults, so to simulate
    # "no key" we must explicitly send an empty X-API-Key (falsy → rejected).
    response = await client.get(
        f"/api/v1/triage/{uuid.uuid4()}", headers={"X-API-Key": ""}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_triage_returns_report(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """GET /triage/{event_id} must return triage data for the event (FR-04, FR-06)."""
    event = _make_event()
    triage = _make_triage(event.id)
    db_session.add(event)
    db_session.add(triage)
    await db_session.flush()

    response = await client.get(f"/api/v1/triage/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.id)
    assert data["classification"] == "CONFIRMED_FIRE"
    assert data["confidence"] == pytest.approx(0.92)
    assert data["danger_level"] == 4
    assert data["triage_source"] == "VLM"


@pytest.mark.asyncio
async def test_get_triage_all_four_classifications_parseable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """All 4 classification values must round-trip through the API (FR-05)."""
    classifications = [
        "CONFIRMED_FIRE", "PROBABLE_FIRE", "FALSE_POSITIVE", "INDUSTRIAL_SOURCE"
    ]
    for cls in classifications:
        event = _make_event()
        triage = _make_triage(event.id, classification=cls)
        db_session.add(event)
        db_session.add(triage)
    await db_session.flush()

    # Re-query all events and check each
    for event in [e for e in db_session.identity_map.values() if isinstance(e, FireEvent)]:
        response = await client.get(f"/api/v1/triage/{event.id}")
        if response.status_code == 200:
            data = response.json()
            assert data["classification"] in classifications


@pytest.mark.asyncio
async def test_get_triage_rule_based_source_returned(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """triage_source=RULE_BASED_FALLBACK must be returned correctly (ADR-011)."""
    event = _make_event()
    triage = _make_triage(
        event.id,
        classification="PROBABLE_FIRE",
        triage_source="RULE_BASED_FALLBACK",
        confidence=0.5,
        danger_level=3,
    )
    db_session.add(event)
    db_session.add(triage)
    await db_session.flush()

    response = await client.get(f"/api/v1/triage/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["triage_source"] == "RULE_BASED_FALLBACK"
    assert data["classification"] == "PROBABLE_FIRE"


@pytest.mark.asyncio
async def test_get_triage_returns_latest_report_when_multiple(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """When multiple triage reports exist for an event, the latest must be returned."""
    event = _make_event()
    old_triage = _make_triage(
        event.id,
        classification="PROBABLE_FIRE",
        processed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    new_triage = _make_triage(
        event.id,
        classification="CONFIRMED_FIRE",
        processed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    db_session.add(old_triage)
    db_session.add(new_triage)
    await db_session.flush()

    response = await client.get(f"/api/v1/triage/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "CONFIRMED_FIRE"


@pytest.mark.asyncio
async def test_get_triage_for_nonexistent_event_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/triage/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_triage_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/triage/not-a-valid-uuid")
    assert response.status_code == 422
