"""
Fire event writer — upserts normalized FIRMS data into the fire_events table.
Skips duplicate events based on firms_id uniqueness constraint.
"""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent
from app.schemas.fire_event import FireEventCreate

logger = structlog.get_logger()


async def upsert_fire_events(
    events: list[dict],
    db: AsyncSession,
) -> tuple[list[str], int]:
    """
    Insert new fire events, skipping those already in the DB (by firms_id).

    Returns:
        (new_event_ids, skipped_count)
    """
    if not events:
        return [], 0

    # Collect all firms_ids from this batch
    firms_ids = [e["firms_id"] for e in events if e.get("firms_id")]

    # Query existing firms_ids in one shot
    existing_result = await db.execute(
        select(FireEvent.firms_id).where(FireEvent.firms_id.in_(firms_ids))
    )
    existing_ids: set[str] = {row[0] for row in existing_result.fetchall()}

    new_events: list[FireEvent] = []
    skipped = 0

    for event_dict in events:
        fid = event_dict.get("firms_id")
        if fid and fid in existing_ids:
            skipped += 1
            continue

        schema = FireEventCreate(**event_dict)
        db_event = FireEvent(
            id=uuid.uuid4(),
            firms_id=schema.firms_id,
            detected_at=schema.detected_at,
            lat=schema.lat,
            lon=schema.lon,
            frp=schema.frp,
            brightness=schema.brightness,
            satellite=schema.satellite,
            tile_url=schema.tile_url,
            status="PENDING",
        )
        db.add(db_event)
        new_events.append(db_event)

    await db.flush()
    new_ids = [str(event.id) for event in new_events]

    logger.info(
        "fire_events_upserted",
        new=len(new_ids),
        skipped=skipped,
        total_input=len(events),
    )
    return new_ids, skipped
