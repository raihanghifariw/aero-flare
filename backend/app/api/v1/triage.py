"""
Triage endpoints.
GET /api/v1/triage/{event_id} — get VLM or rule-based triage report for an event

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.security import limiter
from app.models.triage_report import TriageReport
from app.schemas.common import ErrorResponse, get_trace_id
from app.schemas.triage_report import TriageReportSchema

router = APIRouter(prefix="/triage", tags=["triage"])
logger = structlog.get_logger()


@router.get(
    "/{event_id}",
    response_model=TriageReportSchema,
    summary="Get triage report for an event",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("200/minute")
async def get_triage(
    request: Request,  # required by slowapi
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TriageReportSchema:
    """Retrieve the VLM triage report for a given fire event UUID."""
    result = await db.execute(
        select(TriageReport)
        .where(TriageReport.event_id == event_id)
        .order_by(TriageReport.processed_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="TRIAGE_NOT_FOUND",
                message=f"No triage report for event_id={event_id}",
                trace_id=get_trace_id(),
            ).model_dump(mode="json"),
        )
    return TriageReportSchema.model_validate(report)
