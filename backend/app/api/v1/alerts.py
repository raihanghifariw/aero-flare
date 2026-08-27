"""
Retry alerts endpoint.
POST /api/v1/alerts/retry/{event_id} — re-attempt delivery for ALERTED_FAILED events.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.fire_event import FireEvent
from app.schemas.common import ErrorResponse, get_trace_id

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = structlog.get_logger()


class AlertRetryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    message: str


@router.post(
    "/retry/{event_id}",
    response_model=AlertRetryResponse,
    summary="Retry alert delivery for a failed event",
    dependencies=[Depends(verify_api_key)],
)
async def retry_alert(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertRetryResponse:
    """
    Re-attempt alert delivery for an event with status ALERTED_FAILED.
    Clears alerted_at to allow re-send by the alert service.
    Full retry logic wired in Phase 3 (AGENT-06 Alert Agent).
    """
    result = await db.execute(
        select(FireEvent).where(FireEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="EVENT_NOT_FOUND",
                message=f"No event with id={event_id}",
                trace_id=get_trace_id(),
            ).model_dump(mode="json"),
        )
    if event.status != "ALERTED_FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error="INVALID_STATUS",
                message=f"Event status is '{event.status}', expected 'ALERTED_FAILED'",
                trace_id=get_trace_id(),
            ).model_dump(mode="json"),
        )

    # Clear alerted_at so the alert service treats this as unsent
    await db.execute(
        update(FireEvent)
        .where(FireEvent.id == event_id)
        .values(alerted_at=None, status="PREDICTED")
    )
    logger.info("alert_retry_queued", event_id=str(event_id))

    return AlertRetryResponse(
        event_id=str(event_id),
        message="Alert retry queued. Alert service will re-attempt on next cycle.",
    )
