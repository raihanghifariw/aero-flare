#!/usr/bin/env python
"""
Manual smoke-test for the alert pipeline.

Usage (from backend/ directory):
    python scripts/test_alert.py --event-id <uuid>
    python scripts/test_alert.py --synthetic       # create a fake HIGH-danger event

Requires:
    TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment (or .env).
    DATABASE_URL pointing to a running Postgres instance.

Exit codes:
    0  — all deliveries succeeded
    1  — at least one delivery failed or event not found
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("test_alert")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_alert_for_existing(event_id: str) -> int:
    """Send alert for an already-existing DB event."""
    from app.models.base import async_session_factory
    from app.services.alerts.alert_service import AlertService

    async with async_session_factory() as db:
        svc = AlertService(db)
        result = await svc.send_alert(uuid.UUID(event_id), force=True)

    logger.info("Result: %s", result)
    return 0 if not result.get("skipped") and result.get("telegram_ok") else 1


async def _run_synthetic_alert() -> int:
    """
    Create a synthetic HIGH-danger FireEvent in the DB, run the full alert pipeline,
    then clean up the row.
    """
    from sqlalchemy import delete
    from app.models.base import async_session_factory
    from app.models.fire_event import FireEvent
    from app.services.alerts.alert_service import AlertService

    synthetic_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        event = FireEvent(
            id=synthetic_id,
            source="TEST",
            latitude=-1.5,
            longitude=113.9,
            frp=180.0,
            brightness=420.0,
            confidence="high",
            acquired_at=now,
            status="TRIAGED",
            danger_level="HIGH",
            alert_status="PENDING",
        )
        db.add(event)
        await db.commit()

        svc = AlertService(db)
        result = await svc.send_alert(synthetic_id, force=True)
        logger.info("Synthetic alert result: %s", result)

        # Cleanup
        await db.execute(delete(FireEvent).where(FireEvent.id == synthetic_id))
        await db.commit()

    success = not result.get("skipped") and result.get("telegram_ok")
    return 0 if success else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Aero-Flare alert smoke test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--event-id", help="UUID of an existing FireEvent")
    group.add_argument(
        "--synthetic",
        action="store_true",
        help="Create a synthetic event, alert it, then delete it",
    )
    args = parser.parse_args()

    if args.synthetic:
        exit_code = asyncio.run(_run_synthetic_alert())
    else:
        exit_code = asyncio.run(_run_alert_for_existing(args.event_id))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
