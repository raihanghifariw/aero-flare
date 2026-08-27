"""
Predictions endpoints.
GET /api/v1/predictions/{event_id} — get XGBoost spread prediction for an event

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.security import limiter
from app.models.prediction import Prediction
from app.schemas.common import ErrorResponse, get_trace_id
from app.schemas.prediction import PredictionSchema

router = APIRouter(prefix="/predictions", tags=["predictions"])
logger = structlog.get_logger()


@router.get(
    "/{event_id}",
    response_model=PredictionSchema,
    summary="Get fire spread prediction for an event",
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("200/minute")
async def get_prediction(
    request: Request,  # required by slowapi
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PredictionSchema:
    """Retrieve the XGBoost fire spread prediction for a given event UUID."""
    result = await db.execute(
        select(Prediction)
        .where(Prediction.event_id == event_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error="PREDICTION_NOT_FOUND",
                message=f"No spread prediction for event_id={event_id}",
                trace_id=get_trace_id(),
            ).model_dump(mode="json"),
        )
    return PredictionSchema.model_validate(prediction)
