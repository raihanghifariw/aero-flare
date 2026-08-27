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
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    date_from: datetime | None = Query(None, description="Filter events after this datetime"),
    date_to: datetime | None = Query(None, description="Filter events before this datetime"),
    danger_level: int | None = Query(None, ge=1, le=5, description="Filter by danger level"),
    classification: str | None = Query(None, description="Filter by classification"),
    db: AsyncSession = Depends(get_db),
) -> FireEventsResponse:
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
        # Stratified sampling for initial unfiltered dashboard page 1:
        # Guarantees representation of ALERTED events, Level 1 (False Positives), and general events
        # 1. Up to 50 ALERTED events
        stmt_alerted = select(FireEvent).where(FireEvent.status == "ALERTED").order_by(FireEvent.detected_at.desc()).limit(50)
        alerted_events = (await db.execute(stmt_alerted)).scalars().all()
        alerted_ids = set(e.id for e in alerted_events)

        # 2. Up to 15 Level 1 / FALSE_POSITIVE events
        subq_l1 = select(TriageReport.event_id).where(
            (TriageReport.danger_level == 1) | (TriageReport.classification == "FALSE_POSITIVE")
        )
        stmt_l1 = select(FireEvent).where(FireEvent.id.in_(subq_l1)).order_by(FireEvent.detected_at.desc()).limit(15)
        l1_events = (await db.execute(stmt_l1)).scalars().all()
        l1_ids = set(e.id for e in l1_events)

        # 3. Remaining recent events up to limit
        exclude_ids = alerted_ids | l1_ids
        rem_limit = max(0, limit - len(alerted_events) - len(l1_events))
        stmt_rest = select(FireEvent)
        if exclude_ids:
            stmt_rest = stmt_rest.where(FireEvent.id.notin_(exclude_ids))
        if date_from:
            stmt_rest = stmt_rest.where(FireEvent.detected_at >= date_from)
        if date_to:
            stmt_rest = stmt_rest.where(FireEvent.detected_at <= date_to)
        stmt_rest = stmt_rest.order_by(FireEvent.detected_at.desc()).limit(rem_limit)
        rest_events = (await db.execute(stmt_rest)).scalars().all()

        events = alerted_events + l1_events + rest_events

        # Total count query
        count_stmt = select(func.count(FireEvent.id))
        if date_from:
            count_stmt = count_stmt.where(FireEvent.detected_at >= date_from)
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
    return FireEventsResponse(
        data=event_schemas,
        total=total,
        page=page,
        page_size=limit,
        has_next=(offset + limit) < total,
    )


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
    return FireEventSchema.model_validate(event)
