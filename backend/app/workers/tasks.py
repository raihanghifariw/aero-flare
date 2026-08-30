"""
Celery Task Definitions for Aero-Flare.
Handles NASA FIRMS ingestion, GIBS satellite tile retrieval, Ollama VLM triage,
and XGBoost fire spread predictions.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.cache import cache
from app.core.config import get_settings
from app.models.base import async_session_factory
from app.models.fire_event import FireEvent
from app.services.ingestion.event_writer import upsert_fire_events
from app.services.ingestion.firms_parser import fetch_firms_data, parse_firms_csv
from app.services.ingestion.gibs_tile_fetcher import fetch_and_upload_tile
from app.services.prediction.prediction_service import run_prediction
from app.services.triage.triage_service import run_triage
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


async def _async_process_event(event_id: str) -> dict[str, Any]:
    """
    Async implementation of single fire event processing:
    1. Fetch GIBS TrueColor satellite tile & upload to R2
    2. Run Ollama VLM visual triage
    3. Run XGBoost spread prediction
    4. Invalidate relevant caches
    """
    logger.info("celery_process_event_start", event_id=event_id)
    event_uuid = uuid.UUID(event_id)

    async with async_session_factory() as db:
        result = await db.execute(select(FireEvent).where(FireEvent.id == event_uuid))
        event = result.scalar_one_or_none()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # 1. Tile fetch
        try:
            tile_url = await fetch_and_upload_tile(event)
            if tile_url:
                await db.execute(
                    update(FireEvent).where(FireEvent.id == event.id).values(tile_url=tile_url)
                )
                await db.commit()
                res = await db.execute(select(FireEvent).where(FireEvent.id == event.id))
                event = res.scalar_one()
        except Exception as e:
            logger.warning("celery_tile_fetch_skipped", event_id=event_id, error=str(e))

        # 2. Triage
        triage = await run_triage(event, db=db)
        await db.commit()

        # 3. Spread Prediction (for confirmed / probable fires)
        prediction = None
        if triage.classification in ("CONFIRMED_FIRE", "PROBABLE_FIRE"):
            try:
                prediction = await run_prediction(event, triage, db=db)
                await db.commit()
            except Exception as e:
                logger.error("celery_prediction_failed", event_id=event_id, error=str(e))

    # 4. Invalidate caches atomically
    await cache.delete_pattern("events:*")
    await cache.delete_pattern("stats:*")

    return {
        "event_id": event_id,
        "danger_level": triage.danger_level,
        "classification": triage.classification,
        "prediction_id": str(prediction.id) if prediction else None,
    }


async def _async_ingest_firms(trigger_source: str = "scheduled") -> dict[str, Any]:
    """
    Async implementation of NASA FIRMS ingestion:
    1. Fetch FIRMS CSV
    2. Upsert events into Postgres
    3. Return created event IDs for Celery chaining
    """
    logger.info("celery_firms_ingest_start", trigger=trigger_source)
    settings = get_settings()

    csv_path = await fetch_firms_data(api_key=settings.FIRMS_API_KEY)
    events_data = parse_firms_csv(csv_path)

    async with async_session_factory() as db:
        new_ids, skipped = await upsert_fire_events(events_data, db=db)
        await db.commit()

    # Invalidate caches
    await cache.delete_pattern("events:*")
    await cache.delete_pattern("stats:*")

    return {
        "events_created": len(new_ids),
        "events_skipped": skipped,
        "new_event_ids": [str(eid) for eid in new_ids],
    }


@celery_app.task(bind=True, name="tasks.process_event", max_retries=3, default_retry_delay=60)
def process_event_task(self: Any, event_id: str) -> dict[str, Any]:
    """
    Celery task: Process a single fire event through the entire AI pipeline.
    """
    try:
        return asyncio.run(_async_process_event(event_id))
    except Exception as exc:
        logger.error("process_event_task_failed", event_id=event_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="tasks.ingest_firms", max_retries=2, default_retry_delay=120)
def ingest_firms_task(self: Any, source: str = "scheduled") -> dict[str, Any]:
    """
    Celery task: Ingest FIRMS dataset and spawn downstream process_event tasks.
    """
    try:
        result = asyncio.run(_async_ingest_firms(trigger_source=source))
        new_ids = result.get("new_event_ids", [])

        # Dispatch individual event tasks into worker pool
        for eid in new_ids:
            process_event_task.delay(eid)

        result["enqueued_jobs"] = len(new_ids)
        return result
    except Exception as exc:
        logger.error("ingest_firms_task_failed", trigger=source, error=str(exc))
        raise self.retry(exc=exc)
