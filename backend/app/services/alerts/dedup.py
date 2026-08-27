"""
Alert deduplication via alerted_at DB column.
No Redis — durable across restarts, no external service. (ADR-014)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fire_event import FireEvent

logger = structlog.get_logger()


def is_already_alerted(event: FireEvent) -> bool:
    """
    Return True if this event has already been alerted.
    Checks alerted_at IS NOT NULL — no external service required.
    """
    return event.alerted_at is not None


async def mark_alerted(event_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Set fire_events.alerted_at = NOW() to mark the event as alerted.
    This prevents duplicate alerts on retry without any external state.
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(FireEvent)
        .where(FireEvent.id == event_id)
        .values(alerted_at=now)
    )
    logger.info("alert_marked", event_id=str(event_id), alerted_at=now.isoformat())
