"""
Stats endpoint.
GET /api/v1/stats/summary — aggregate fire event statistics by date range
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.cache import cache
from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport

router = APIRouter(prefix="/stats", tags=["stats"])
logger = structlog.get_logger()


class StatsSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_events: int
    confirmed_fires: int
    probable_fires: int
    false_positives: int
    industrial_sources: int
    alerted_count: int
    vlm_triage_count: int
    rule_based_triage_count: int
    date_from: datetime
    date_to: datetime


@router.get(
    "/summary",
    response_model=StatsSummary,
    summary="Get aggregate fire event statistics",
    dependencies=[Depends(verify_api_key)],
)
async def get_stats_summary(
    date_from: datetime | None = Query(
        None, description="Start of date range (defaults to 7 days ago)"
    ),
    date_to: datetime | None = Query(
        None, description="End of date range (defaults to now)"
    ),
    db: AsyncSession = Depends(get_db),
) -> StatsSummary:
    """Aggregate statistics for fire events over a given date range."""
    cache_key = f"stats:summary:{date_from}:{date_to}"
    cached_stats = await cache.get(cache_key)
    if cached_stats is not None:
        return StatsSummary.model_validate(cached_stats)

    now = datetime.now(timezone.utc)
    _from = date_from or (now - timedelta(days=7))
    _to = date_to or now


    if _from.tzinfo is None:
        _from = _from.replace(tzinfo=timezone.utc)
    if _to.tzinfo is None:
        _to = _to.replace(tzinfo=timezone.utc)

    total = (await db.execute(
        select(func.count(FireEvent.id)).where(
            FireEvent.detected_at >= _from,
            FireEvent.detected_at <= _to,
        )
    )).scalar_one()

    alerted = (await db.execute(
        select(func.count(FireEvent.id)).where(
            FireEvent.detected_at >= _from,
            FireEvent.detected_at <= _to,
            FireEvent.alerted_at.is_not(None),
        )
    )).scalar_one()

    async def _count_by_classification(classification: str) -> int:
        stmt = (
            select(func.count(func.distinct(TriageReport.event_id)))
            .select_from(TriageReport)
            .join(FireEvent, TriageReport.event_id == FireEvent.id)
            .where(
                FireEvent.detected_at >= _from,
                FireEvent.detected_at <= _to,
                TriageReport.classification == classification,
            )
        )
        return (await db.execute(stmt)).scalar_one()

    async def _count_by_source(source: str) -> int:
        stmt = (
            select(func.count(func.distinct(TriageReport.event_id)))
            .select_from(TriageReport)
            .join(FireEvent, TriageReport.event_id == FireEvent.id)
            .where(
                FireEvent.detected_at >= _from,
                FireEvent.detected_at <= _to,
                TriageReport.triage_source == source,
            )
        )
        return (await db.execute(stmt)).scalar_one()

    confirmed = await _count_by_classification("CONFIRMED_FIRE")
    probable = await _count_by_classification("PROBABLE_FIRE")
    fp = await _count_by_classification("FALSE_POSITIVE")
    industrial = await _count_by_classification("INDUSTRIAL_SOURCE")
    vlm_count = await _count_by_source("VLM")
    rule_count = await _count_by_source("RULE_BASED_FALLBACK")

    result = StatsSummary(
        total_events=total,
        confirmed_fires=confirmed,
        probable_fires=probable,
        false_positives=fp,
        industrial_sources=industrial,
        alerted_count=alerted,
        vlm_triage_count=vlm_count,
        rule_based_triage_count=rule_count,
        date_from=_from,
        date_to=_to,
    )
    await cache.set(cache_key, result.model_dump(mode="json"), ttl=60)
    return result

