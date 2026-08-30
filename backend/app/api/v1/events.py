"""
Events endpoints.
GET /api/v1/events        — paginated list with filters (FR-01, FR-18, FR-19)
GET /api/v1/events/{id}   — single event by UUID

NOTE: Do NOT add `from __future__ import annotations` here.
Stringized annotations break FastAPI param resolution on endpoints
wrapped by slowapi's @limiter.limit decorator (wrapper loses module globals).
"""
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.cache import cache
from app.core.security import limiter
from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport
from app.schemas.common import ErrorResponse, get_trace_id
from app.schemas.fire_event import FireEventSchema, FireEventsResponse
from app.schemas.triage_report import TriageReportSchema

router = APIRouter(prefix="/events", tags=["events"])
logger = structlog.get_logger()


@router.get(
    "",
    response_model=FireEventsResponse,
    summary="List fire events",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("100/minute")
async def list_events(
    request: Request,  # required by slowapi
    page: int = Query(1, ge=1, le=10_000, description="Page number"),
    limit: int = Query(50, ge=1, le=1_000, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    date_from: datetime | None = Query(None, description="Filter events after this datetime"),
    date_to: datetime | None = Query(None, description="Filter events before this datetime"),
    danger_level: int | None = Query(None, ge=1, le=5, description="Filter by danger level"),
    classification: str | None = Query(None, description="Filter by classification"),
    db: AsyncSession = Depends(get_db),
) -> FireEventsResponse:
    # 1. Check cache for instantaneous response
    cache_key = f"events:list:{page}:{limit}:{status}:{date_from}:{date_to}:{danger_level}:{classification}"
    cached_data = await cache.get(cache_key)
    if cached_data is not None:
        return FireEventsResponse.model_validate(cached_data)


    # Subquery filtering for danger_level or classification
    if danger_level is not None or classification is not None:
        tr_subq = select(TriageReport.event_id)
        if danger_level is not None:
            tr_subq = tr_subq.where(TriageReport.danger_level == danger_level)
        if classification:
            tr_subq = tr_subq.where(TriageReport.classification == classification)

        stmt = select(FireEvent).where(FireEvent.id.in_(tr_subq)).order_by(FireEvent.detected_at.desc())
        if status:
            stmt = stmt.where(FireEvent.status == status)
        if date_from:
            stmt = stmt.where(FireEvent.detected_at >= date_from)
        if date_to:
            stmt = stmt.where(FireEvent.detected_at <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * limit
        result = await db.execute(stmt.limit(limit).offset(offset))
        events = result.scalars().all()
    elif not status and page == 1:
        # Nationwide balanced regional sampling for initial unfiltered dashboard:
        # Guarantees representation across all major Indonesian regions (Sumatra, Kalimantan/Java, Sulawesi/Maluku, Papua)
        from sqlalchemy import and_, case

        # 1. Guarantee representation of FALSE_POSITIVE / Level 1 events
        fp_subq = select(TriageReport.event_id).where(
            (TriageReport.classification == "FALSE_POSITIVE") | (TriageReport.danger_level == 1)
        )
        stmt_fp = select(FireEvent).where(FireEvent.id.in_(fp_subq))
        if date_from:
            stmt_fp = stmt_fp.where(FireEvent.detected_at >= date_from)
        if date_to:
            stmt_fp = stmt_fp.where(FireEvent.detected_at <= date_to)
        stmt_fp = stmt_fp.order_by(FireEvent.detected_at.desc()).limit(15)
        fp_events = (await db.execute(stmt_fp)).scalars().all()

        sampled_events = list(fp_events)
        seen_ids = set(e.id for e in fp_events)

        # 2. Nationwide balanced regional sampling for remaining slots
        sectors = [
            FireEvent.lon < 109,                               # Sumatra & West
            and_(FireEvent.lon >= 109, FireEvent.lon < 119),   # Kalimantan & Java
            and_(FireEvent.lon >= 119, FireEvent.lon < 130),   # Sulawesi & Maluku & Nusa
            FireEvent.lon >= 130,                              # Papua & East
        ]

        rem_limit = max(0, limit - len(sampled_events))
        per_sector = max(1, rem_limit // len(sectors))

        for sector_cond in sectors:
            stmt_sector = select(FireEvent).where(sector_cond)
            if seen_ids:
                stmt_sector = stmt_sector.where(FireEvent.id.notin_(seen_ids))
            if date_from:
                stmt_sector = stmt_sector.where(FireEvent.detected_at >= date_from)
            if date_to:
                stmt_sector = stmt_sector.where(FireEvent.detected_at <= date_to)

            stmt_sector = stmt_sector.order_by(
                case((FireEvent.status == "ALERTED", 0), else_=1),
                FireEvent.detected_at.desc(),
            ).limit(per_sector)

            res_sector = await db.execute(stmt_sector)
            for e in res_sector.scalars().all():
                if e.id not in seen_ids:
                    seen_ids.add(e.id)
                    sampled_events.append(e)

        # Backfill with remaining recent events if under limit
        if len(sampled_events) < limit:
            rem_needed = limit - len(sampled_events)
            stmt_backfill = select(FireEvent)
            if seen_ids:
                stmt_backfill = stmt_backfill.where(FireEvent.id.notin_(seen_ids))
            if date_from:
                stmt_backfill = stmt_backfill.where(FireEvent.detected_at >= date_from)
            if date_to:
                stmt_backfill = stmt_backfill.where(FireEvent.detected_at <= date_to)
            stmt_backfill = stmt_backfill.order_by(FireEvent.detected_at.desc()).limit(rem_needed)
            res_backfill = await db.execute(stmt_backfill)
            for e in res_backfill.scalars().all():
                if e.id not in seen_ids:
                    seen_ids.add(e.id)
                    sampled_events.append(e)

        # Sort combined nationwide sample chronologically (latest first) and truncate to limit
        sampled_events.sort(key=lambda x: x.detected_at, reverse=True)
        events = sampled_events[:limit]

        # Total count query within date range
        count_stmt = select(func.count(FireEvent.id))
        if date_from:
            count_stmt = count_stmt.where(FireEvent.detected_at >= date_from)
        if date_to:
            count_stmt = count_stmt.where(FireEvent.detected_at <= date_to)
        total = (await db.execute(count_stmt)).scalar_one()
    else:
        # Regular fallback pagination
        stmt = select(FireEvent).order_by(FireEvent.detected_at.desc())
        if status:
            stmt = stmt.where(FireEvent.status == status)
        if date_from:
            stmt = stmt.where(FireEvent.detected_at >= date_from)
        if date_to:
            stmt = stmt.where(FireEvent.detected_at <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * limit
        result = await db.execute(stmt.limit(limit).offset(offset))
        events = result.scalars().all()

    # Batch load latest TriageReport for returned events
    event_ids = [e.id for e in events]
    triage_map: dict[uuid.UUID, TriageReport] = {}
    if event_ids:
        triage_stmt = (
            select(TriageReport)
            .where(TriageReport.event_id.in_(event_ids))
            .order_by(TriageReport.processed_at.desc())
        )
        triage_res = await db.execute(triage_stmt)
        for tr in triage_res.scalars().all():
            if tr.event_id not in triage_map:
                triage_map[tr.event_id] = tr

    event_schemas = []
    for e in events:
        schema = FireEventSchema.model_validate(e)
        tr = triage_map.get(e.id)
        if tr:
            schema = schema.model_copy(update={"triage": TriageReportSchema.model_validate(tr)})
        event_schemas.append(schema)

    offset = (page - 1) * limit
    response = FireEventsResponse(
        data=event_schemas,
        total=total,
        page=page,
        page_size=limit,
        has_next=(offset + limit) < total,
    )
    # Cache list for 15 seconds
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=15)
    return response


@router.get(
    "/{event_id}",
    response_model=FireEventSchema,
    summary="Get a single fire event",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("200/minute")
async def get_event(
    request: Request,  # required by slowapi
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FireEventSchema:
    """Retrieve a single fire event by its UUID."""
    cache_key = f"events:detail:{event_id}"
    cached_event = await cache.get(cache_key)
    if cached_event is not None:
        return FireEventSchema.model_validate(cached_event)

    result = await db.execute(
        select(FireEvent).where(FireEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="EVENT_NOT_FOUND",
                message=f"No fire event with id={event_id}",
                trace_id=get_trace_id(),
            ).model_dump(mode="json"),
        )
    schema = FireEventSchema.model_validate(event)
    await cache.set(cache_key, schema.model_dump(mode="json"), ttl=60)
    return schema

