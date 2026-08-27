"""
Stats endpoint.
GET /api/v1/stats/summary — aggregate fire event statistics by date range
"""
from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
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
    now = datetime.utcnow()
    _from = date_from or (now - timedelta(days=7))
    _to = date_to or now

    # Base filter
    base = select(FireEvent).where(
        FireEvent.detected_at >= _from,
        FireEvent.detected_at <= _to,
    )

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    alerted = (await db.execute(
        select(func.count()).select_from(
            base.where(FireEvent.alerted_at.is_not(None)).subquery()
        )
    )).scalar_one()

    def _triage_count(classification: str) -> select:  # type: ignore[return]
        return select(func.count()).select_from(
            select(TriageReport).join(
                FireEvent, TriageReport.event_id == FireEvent.id
            ).where(
                FireEvent.detected_at >= _from,
                FireEvent.detected_at <= _to,
                TriageReport.classification == classification,
            ).subquery()
        )

    def _source_count(source: str) -> select:  # type: ignore[return]
        return select(func.count()).select_from(
            select(TriageReport).join(
                FireEvent, TriageReport.event_id == FireEvent.id
            ).where(
                FireEvent.detected_at >= _from,
                FireEvent.detected_at <= _to,
                TriageReport.triage_source == source,
            ).subquery()
        )

    confirmed = (await db.execute(_triage_count("CONFIRMED_FIRE"))).scalar_one()
    probable = (await db.execute(_triage_count("PROBABLE_FIRE"))).scalar_one()
    fp = (await db.execute(_triage_count("FALSE_POSITIVE"))).scalar_one()
    industrial = (await db.execute(_triage_count("INDUSTRIAL_SOURCE"))).scalar_one()
    vlm_count = (await db.execute(_source_count("VLM"))).scalar_one()
    rule_count = (await db.execute(_source_count("RULE_BASED_FALLBACK"))).scalar_one()

    return StatsSummary(
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
