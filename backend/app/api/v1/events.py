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
from app.schemas.common import ErrorResponse, get_trace_id
from app.schemas.fire_event import FireEventSchema, FireEventsResponse

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
    db: AsyncSession = Depends(get_db),
) -> FireEventsResponse:
    """Retrieve a paginated list of fire events with optional filters."""
    stmt = select(FireEvent).order_by(FireEvent.detected_at.desc())

    if status:
        stmt = stmt.where(FireEvent.status == status)
    if date_from:
        stmt = stmt.where(FireEvent.detected_at >= date_from)
    if date_to:
        stmt = stmt.where(FireEvent.detected_at <= date_to)

    # Count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    result = await db.execute(stmt.limit(limit).offset(offset))
    events = result.scalars().all()

    return FireEventsResponse(
        data=[FireEventSchema.model_validate(e) for e in events],
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
