"""
Integration tests for the Events API endpoints.
Uses in-memory SQLite DB (via conftest.py) + AsyncClient — no live backend needed.

Covers: FR-18 (REST API), FR-19 (Pagination), auth gate (NFR-04).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent

# ─── Helpers ─────────────────────────────────────────────────────────────────

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
        status="PENDING",
        alerted_at=None,
    )
    defaults.update(kwargs)
    return FireEvent(**defaults)


# ─── Auth tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_events_without_api_key_returns_403(client: AsyncClient) -> None:
    """All protected endpoints must return 403 without a valid X-API-Key."""
    # httpx merges request headers with client-level defaults, so to simulate
    # "no key" we must explicitly send an empty X-API-Key (falsy → rejected).
    response = await client.get("/api/v1/events", headers={"X-API-Key": ""})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_events_with_wrong_api_key_returns_403(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/events",
        headers={"X-API-Key": "definitely-wrong-key"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_health_endpoint_returns_200_without_auth(client: AsyncClient) -> None:
    """Health endpoint must be publicly accessible (no auth)."""
    response = await client.get("/api/v1/health", headers={})
    # Accept 200 or 503 (503 means DB/Ollama degraded, but endpoint is reachable)
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "components" in data


# ─── Events list ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_events_empty_db_returns_empty_list(client: AsyncClient) -> None:
    """Empty DB should return data=[] with total=0."""
    response = await client.get("/api/v1/events")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_events_returns_inserted_events(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Events inserted into DB should appear in the API response."""
    event1 = _make_event(lat=-2.0, lon=112.0)
    event2 = _make_event(lat=-3.0, lon=113.0)
    db_session.add_all([event1, event2])
    await db_session.flush()

    response = await client.get("/api/v1/events")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_events_pagination_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """limit query param must restrict number of returned events (FR-19)."""
    for _ in range(5):
        db_session.add(_make_event())
    await db_session.flush()

    response = await client.get("/api/v1/events?limit=2&page=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["total"] == 5
    assert data["has_next"] is True


@pytest.mark.asyncio
async def test_get_events_pagination_page2(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Page 2 should return the remaining events."""
    for _ in range(3):
        db_session.add(_make_event())
    await db_session.flush()

    response = await client.get("/api/v1/events?limit=2&page=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["has_next"] is False


@pytest.mark.asyncio
async def test_get_events_invalid_limit_returns_422(client: AsyncClient) -> None:
    """limit > 200 must be rejected with 422 Unprocessable Entity."""
    response = await client.get("/api/v1/events?limit=99999")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_events_status_filter(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """status filter must only return events with matching status."""
    db_session.add(_make_event(status="PENDING"))
    db_session.add(_make_event(status="TRIAGED"))
    db_session.add(_make_event(status="TRIAGED"))
    await db_session.flush()

    response = await client.get("/api/v1/events?status=TRIAGED")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(e["status"] == "TRIAGED" for e in data["data"])


# ─── Single event ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_event_by_id_returns_event(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """GET /events/{id} must return the correct event."""
    event = _make_event()
    db_session.add(event)
    await db_session.flush()

    response = await client.get(f"/api/v1/events/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(event.id)
    assert data["satellite"] == event.satellite


@pytest.mark.asyncio
async def test_get_event_by_invalid_uuid_returns_422(client: AsyncClient) -> None:
    """Non-UUID path param must return 422."""
    response = await client.get("/api/v1/events/not-a-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_event_by_nonexistent_uuid_returns_404(client: AsyncClient) -> None:
    """Valid UUID not in DB must return 404."""
    response = await client.get(f"/api/v1/events/{uuid.uuid4()}")
    assert response.status_code == 404
    data = response.json()
    # Error body must include trace_id (NFR-08)
    detail = data.get("detail", {})
    assert "trace_id" in detail or "trace_id" in str(detail)
