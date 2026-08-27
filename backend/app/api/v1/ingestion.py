"""
Ingestion trigger endpoint — wired to the full pipeline (Phase 2 update).
POST /api/v1/ingestion/trigger — called by GitHub Actions pipeline every 3 hours.

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.config import get_settings
from app.core.security import limiter
from app.models.fire_event import FireEvent

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = structlog.get_logger()
TRIAGE_BATCH_SIZE = 50


class IngestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    events_created: int = 0
    events_skipped: int = 0


async def _run_pipeline(db: AsyncSession) -> tuple[int, int]:
    """Full ingestion + triage + prediction pipeline (background task)."""
    from app.services.ingestion.event_writer import upsert_fire_events
    from app.services.ingestion.firms_parser import fetch_firms_data, parse_firms_csv
    from app.services.ingestion.gibs_tile_fetcher import fetch_gibs_tile
    from app.services.prediction.prediction_service import run_prediction
    from app.services.triage.triage_service import run_triage

    settings = get_settings()

    # 1. Fetch FIRMS CSV
    csv_path = await fetch_firms_data(api_key=settings.FIRMS_API_KEY)

    # 2. Parse + deduplicate
    events_data = parse_firms_csv(csv_path)

    # 3. Upsert events
    new_ids, skipped = await upsert_fire_events(events_data, db)
    await db.commit()

    # Process new events and resume pending events left by an interrupted run.
    result = await db.execute(
        select(FireEvent)
        .where(
            FireEvent.id.in_(new_ids)
            if new_ids
            else FireEvent.status == "PENDING"
        )
        .order_by(FireEvent.frp.desc().nullslast(), FireEvent.detected_at.desc())
        .limit(TRIAGE_BATCH_SIZE)
    )
    new_events = result.scalars().all()

    if not new_events:
        logger.info("ingestion_no_pending_events", skipped=skipped)
        return 0, skipped

    # 4. For each event: fetch GIBS tile → triage → predict

    for event in new_events:
        # Fetch tile
        from datetime import timezone
        date_str = event.detected_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        try:
            r2_key = await fetch_gibs_tile(event.lat, event.lon, date_str, str(event.id))
            if r2_key:
                from sqlalchemy import update
                await db.execute(
                    update(FireEvent).where(FireEvent.id == event.id).values(tile_url=r2_key)
                )
                await db.commit()
                await db.refresh(event)
        except Exception as exc:
            logger.warning("tile_fetch_skipped", event_id=str(event.id), error=str(exc))

        # Triage
        try:
            triage_report = await run_triage(event, db)
            await db.commit()
        except Exception as exc:
            logger.warning("triage_skipped", event_id=str(event.id), error=str(exc))
            await db.rollback()
            continue

        # Prediction (only for confirmed/probable fires)
        if triage_report.classification in ("CONFIRMED_FIRE", "PROBABLE_FIRE"):
            try:
                await run_prediction(event, triage_report, db)
                await db.commit()
            except Exception as e:
                logger.warning(
                    "prediction_skipped", event_id=str(event.id), error=str(e)
                )

    logger.info("pipeline_complete", processed=len(new_events), new=len(new_ids), skipped=skipped)
    return len(new_events), skipped


@router.post(
    "/trigger",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger FIRMS ingestion pipeline",
    description=(
        "Called by GitHub Actions firms_ingest.yml every 3 hours. "
        "Pulls latest FIRMS data, fetches GIBS tiles, runs VLM triage, "
        "triggers XGBoost predictions, and dispatches alerts."
    ),
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("10/minute")
async def trigger_ingestion(
    request: Request,  # required by slowapi
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger the full FIRMS ingestion + triage pipeline.
    Returns 202 immediately; pipeline runs in background.
    """
    logger.info("ingestion_trigger_received")
    background_tasks.add_task(_run_pipeline, db)

    return IngestionResponse(
        message="Ingestion pipeline triggered. Processing in background.",
    )
