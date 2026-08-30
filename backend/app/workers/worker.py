"""
Aero-Flare Distributed Background Worker.
Processes queued tasks: NASA FIRMS ingestion, GIBS satellite tile fetching,
Ollama VLM visual triage, XGBoost spread prediction, and alert dispatching.

Usage:
    python -m app.workers.worker
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import uuid
from typing import Any

import structlog
from sqlalchemy import select, update

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.cache import cache
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.queue import task_queue
from app.models.base import async_session_factory
from app.models.fire_event import FireEvent
from app.services.ingestion.firms_parser import fetch_firms_data, parse_firms_csv
from app.services.ingestion.gibs_tile_fetcher import fetch_and_upload_tile
from app.services.prediction.prediction_service import run_prediction
from app.services.triage.triage_service import run_triage

logger = structlog.get_logger()

MAX_CONCURRENT_TASKS = 6


async def process_event_task(event_id: str) -> dict[str, Any]:
    """
    Process a single fire event end-to-end:
    1. Fetch GIBS TrueColor satellite tile & upload to R2
    2. Run Ollama VLM triage (or rule-based fallback)
    3. Run XGBoost spread prediction
    4. Automatically invalidate cache
    """
    logger.info("worker_process_event_start", event_id=event_id)
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
            logger.warning("worker_tile_fetch_skipped", event_id=event_id, error=str(e))

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
                logger.error("worker_prediction_failed", event_id=event_id, error=str(e))

    # 4. Invalidate event & stats caches atomically
    await cache.delete_pattern("events:*")
    await cache.delete_pattern("stats:*")

    return {
        "event_id": event_id,
        "danger_level": triage.danger_level,
        "classification": triage.classification,
        "prediction_id": str(prediction.id) if prediction else None,
    }


async def ingest_firms_task(trigger_source: str = "scheduled") -> dict[str, Any]:
    """
    Ingest FIRMS CSV, upsert events into Postgres, and enqueue individual event jobs.
    """
    logger.info("worker_firms_ingest_start", trigger=trigger_source)
    settings = get_settings()
    from app.services.ingestion.event_writer import upsert_fire_events

    csv_path = await fetch_firms_data(api_key=settings.FIRMS_API_KEY)
    events_data = parse_firms_csv(csv_path)

    async with async_session_factory() as db:
        new_ids, skipped = await upsert_fire_events(events_data, db=db)
        await db.commit()

    # Enqueue processing for each new event
    for eid in new_ids:
        await task_queue.enqueue("process_event", {"event_id": eid})

    # Invalidate caches
    await cache.delete_pattern("events:*")
    await cache.delete_pattern("stats:*")

    return {
        "events_created": len(new_ids),
        "events_skipped": skipped,
        "enqueued_jobs": len(new_ids),
    }


async def handle_job(job: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    """Execute a popped job with status tracking and concurrency semaphore."""
    async with semaphore:
        job_id = job["job_id"]
        task_name = job["task_name"]
        payload = job.get("payload", {})

        logger.info("worker_executing_job", job_id=job_id, task=task_name)
        await task_queue.update_job_status(job_id, "running")

        try:
            if task_name == "process_event":
                result = await process_event_task(payload["event_id"])
            elif task_name == "ingest_firms":
                result = await ingest_firms_task(payload.get("source", "manual"))
            else:
                raise ValueError(f"Unknown task name: {task_name}")

            await task_queue.update_job_status(job_id, "completed", result=result)
            logger.info("worker_job_completed", job_id=job_id, task=task_name)
        except Exception as exc:
            logger.error("worker_job_failed", job_id=job_id, task=task_name, error=str(exc))
            await task_queue.update_job_status(job_id, "failed", error=str(exc))


async def run_worker() -> None:
    """Continuous worker loop."""
    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)
    logger.info("worker_pool_started", concurrency=MAX_CONCURRENT_TASKS)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    running = True

    def _signal_handler() -> None:
        nonlocal running
        logger.info("worker_shutdown_signal_received")
        running = False

    import contextlib

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_handler)


    while running:
        try:
            job = await task_queue.pop_job(timeout=2)
            if job:
                asyncio.create_task(handle_job(job, semaphore))
        except Exception as e:
            logger.warning("worker_loop_error", error=str(e))
            await asyncio.sleep(1.0)

    logger.info("worker_pool_stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())
