"""
Standalone FIRMS ingestion script — called by GitHub Actions firms_ingest.yml
every 3 hours. Runs the full ingestion + triage + prediction + alert pipeline.

Usage:
    python backend/scripts/ingest_firms.py

Environment variables read from .env or GitHub Actions secrets.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Add backend/ to path so app.* imports work when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main() -> None:
    """Full FIRMS ingestion pipeline:
      1. Fetch FIRMS CSV from NASA API (last 24h, Indonesia bbox)
      2. Parse + deduplicate events
      3. Fetch GIBS tile + upload to R2 for each new event
      4. Upsert FireEvent rows into Postgres
      5. Run triage (VLM or rule-based fallback) for each new event
      6. Run XGBoost spread prediction for triaged events
      7. Alert service fires automatically from prediction_service / triage_service
    """
    from app.core.config import get_settings
    from app.core.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)

    import structlog

    logger = structlog.get_logger()

    logger.info(
        "ingest_firms_start",
        firms_api_key_set=bool(settings.FIRMS_API_KEY),
        ollama_base_url=settings.OLLAMA_BASE_URL,
    )

    from app.models.base import async_session_factory
    from app.services.ingestion.firms_parser import fetch_firms_data, parse_firms_csv
    from app.services.ingestion.gibs_tile_fetcher import fetch_and_upload_tile
    from app.services.prediction.prediction_service import run_prediction
    from app.services.triage.triage_service import run_triage

    # ------------------------------------------------------------------ #
    # Step 1 — Fetch + parse FIRMS                                         #
    # ------------------------------------------------------------------ #
    logger.info("ingest_firms.step1_fetch_firms")
    csv_path = await fetch_firms_data(
        api_key=settings.FIRMS_API_KEY,
    )
    events_data = parse_firms_csv(csv_path)
    logger.info("ingest_firms.firms_parsed", count=len(events_data))

    if not events_data:
        logger.info("ingest_firms.no_new_events")
        return

    # ------------------------------------------------------------------ #
    # Step 2 — Upsert + fetch tiles                                        #
    # ------------------------------------------------------------------ #
    logger.info("ingest_firms.step2_upsert_events")
    async with async_session_factory() as db:
        from app.services.ingestion.event_writer import upsert_fire_events
        new_ids, skipped = await upsert_fire_events(events_data, db=db)
        await db.commit()
    new_event_ids = new_ids
    logger.info("ingest_firms.events_upserted", new=len(new_event_ids), skipped=skipped)

    # ------------------------------------------------------------------ #
    # Step 3 — Fetch GIBS tiles and triage each new event                  #
    # ------------------------------------------------------------------ #
    if not new_event_ids:
        logger.info("ingest_firms.no_new_events")
        return

    from sqlalchemy import select as sa_select

    from app.models.fire_event import FireEvent

    async with async_session_factory() as db:
        result = await db.execute(
            sa_select(FireEvent)
            .where(FireEvent.id.in_([
                __import__('uuid').UUID(eid) for eid in new_event_ids
            ]))
            .order_by(FireEvent.frp.desc().nullslast())
        )
        new_events = result.scalars().all()

    for event in new_events:
        async with async_session_factory() as db:
            # Fetch tile (non-blocking, errors soft-fail)
            try:
                tile_url = await fetch_and_upload_tile(event)
                if tile_url:
                    from sqlalchemy import update

                    from app.models.fire_event import FireEvent
                    await db.execute(
                        update(FireEvent)
                        .where(FireEvent.id == event.id)
                        .values(tile_url=tile_url)
                    )
                    await db.commit()
                    # Reload so triage sees tile_url
                    from sqlalchemy import select
                    result = await db.execute(
                        select(FireEvent).where(FireEvent.id == event.id)
                    )
                    event = result.scalar_one()
            except Exception as tile_exc:  # noqa: BLE001
                logger.warning(
                    "ingest_firms.tile_fetch_failed",
                    event_id=str(event.id),
                    error=str(tile_exc),
                )

            # Triage
            try:
                triage = await run_triage(event, db=db)
                await db.commit()
                logger.info(
                    "ingest_firms.triage_complete",
                    event_id=str(event.id),
                    source=triage.triage_source,
                    danger=triage.danger_level,
                )
            except Exception as triage_exc:  # noqa: BLE001
                logger.error(
                    "ingest_firms.triage_failed",
                    event_id=str(event.id),
                    error=str(triage_exc),
                )
                continue

            # Prediction (only for VLM-triaged events — rule-based already alerted)
            if triage.triage_source == "VLM":
                try:
                    await run_prediction(event, triage, db=db)
                    await db.commit()
                except Exception as pred_exc:  # noqa: BLE001
                    logger.error(
                        "ingest_firms.prediction_failed",
                        event_id=str(event.id),
                        error=str(pred_exc),
                    )

    logger.info("ingest_firms_done", processed=len(new_events))


if __name__ == "__main__":
    asyncio.run(main())
