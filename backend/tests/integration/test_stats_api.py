"""
Integration tests for Stats API (GET /api/v1/stats/summary).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport


@pytest.mark.asyncio
async def test_stats_summary_full_flow(client: AsyncClient, db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    event1 = FireEvent(
        id=uuid.uuid4(),
        firms_id="firms_s1",
        detected_at=now - timedelta(days=1),
        lat=-2.0,
        lon=112.0,
        frp=50.0,
        brightness=320.0,
        satellite="NOAA-20",
        status="ALERTED",
        alerted_at=now - timedelta(days=1),
    )
    event2 = FireEvent(
        id=uuid.uuid4(),
        firms_id="firms_s2",
        detected_at=now - timedelta(days=2),
        lat=-3.0,
        lon=113.0,
        frp=20.0,
        brightness=305.0,
        satellite="NOAA-20",
        status="TRIAGED",
    )
    db_session.add_all([event1, event2])
    await db_session.flush()

    tr1 = TriageReport(
        id=uuid.uuid4(),
        event_id=event1.id,
        classification="CONFIRMED_FIRE",
        danger_level=5,
        confidence=0.95,
        triage_source="VLM",
        summary="Active flame",
        recommended_action="DISPATCH",
        processed_at=now,
    )
    tr2 = TriageReport(
        id=uuid.uuid4(),
        event_id=event2.id,
        classification="FALSE_POSITIVE",
        danger_level=1,
        confidence=0.8,
        triage_source="RULE_BASED_FALLBACK",
        summary="Sun reflection",
        recommended_action="NO_ACTION",
        processed_at=now,
    )
    db_session.add_all([tr1, tr2])
    await db_session.flush()

    date_from = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    date_to = now.strftime("%Y-%m-%dT%H:%M:%S")

    response = await client.get(f"/api/v1/stats/summary?date_from={date_from}&date_to={date_to}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 2
    assert data["confirmed_fires"] == 1
    assert data["false_positives"] == 1
    assert data["alerted_count"] == 1
    assert data["vlm_triage_count"] == 1
    assert data["rule_based_triage_count"] == 1
