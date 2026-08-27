"""Authenticated satellite tile access."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.security import limiter
from app.models.fire_event import FireEvent
from app.services.ingestion.gibs_tile_fetcher import get_r2_presigned_url

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get(
    "/{event_id}",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("60/minute")
async def get_tile(
    request: Request,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Redirect an authenticated tile request to a short-lived R2 URL."""
    result = await db.execute(select(FireEvent.tile_url).where(FireEvent.id == event_id))
    tile_key = result.scalar_one_or_none()
    if not tile_key:
        raise HTTPException(status_code=404, detail="Satellite tile not available")

    return RedirectResponse(get_r2_presigned_url(tile_key), status_code=307)
