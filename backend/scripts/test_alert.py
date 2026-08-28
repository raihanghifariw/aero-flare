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
from pathlib import Path

from dotenv import load_dotenv

# Load .env from aero-flare root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    Create a synthetic HIGH-danger FireEvent in the DB with full triage and prediction,
    run the alert pipeline to test Telegram delivery, then clean up.
    """
    from sqlalchemy import delete

    from app.models.base import async_session_factory
    from app.models.fire_event import FireEvent
    from app.models.prediction import Prediction
    from app.models.triage_report import TriageReport
    from app.services.alerts.alert_service import AlertService

    synthetic_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        event = FireEvent(
            id=synthetic_id,
            firms_id=f"TEST_{synthetic_id.hex[:8]}",
            lat=-2.3145,
            lon=113.8920,
            frp=88.6,
            brightness=385.2,
            satellite="VIIRS-NOAA20",
            detected_at=now,
            status="TRIAGED",
        )
        db.add(event)

        triage = TriageReport(
            id=uuid.uuid4(),
            event_id=synthetic_id,
            classification="CONFIRMED_FIRE",
            danger_level=4,
            confidence=0.94,
            fire_area_ha=14.5,
            smoke_direction="E",
            cloud_cover_percent=12.0,
            visually_obscured=False,
            summary="Terdeteksi kolom asap tebal menjalar ke timur dengan konsentrasi panas termal tinggi di area tutupan lahan gambut.",
            recommended_action="DISPATCH_WATER_BOMBING",
            triage_source="VLM",
            processed_at=now,
        )
        db.add(triage)

        pred = Prediction(
            id=uuid.uuid4(),
            event_id=synthetic_id,
            spread_direction_deg=90.0,
            radius_6h_km=4.2,
            radius_12h_km=8.5,
            radius_24h_km=14.0,
            wind_speed=15.2,
            wind_direction=85.0,
            humidity=45.0,
            model_version="xgboost_v1.0",
            predicted_at=now,
        )
        db.add(pred)
        await db.commit()

        svc = AlertService(db)
        result = await svc.send_alert(synthetic_id, force=True)
        logger.info("Synthetic alert result: %s", result)

        # Cleanup
        await db.execute(delete(Prediction).where(Prediction.event_id == synthetic_id))
        await db.execute(delete(TriageReport).where(TriageReport.event_id == synthetic_id))
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
