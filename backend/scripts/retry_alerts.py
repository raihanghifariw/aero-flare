"""
Standalone alert retry script — called by GitHub Actions alert_retry.yml every 30 min.
Re-attempts delivery for events with alert_status = 'ALERTED_FAILED'.

Usage:
    python backend/scripts/retry_alerts.py [--limit N]

Exit codes:
    0 — completed (even if some retries fail — the scheduler should not crash)
    1 — unexpected fatal error
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main(limit: int) -> None:
    from app.core.config import get_settings
    from app.core.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)

    import structlog

    logger = structlog.get_logger()

    logger.info("retry_alerts_start", limit=limit)

    from app.models.base import async_session_factory
    from app.services.alerts.alert_service import AlertService

    async with async_session_factory() as db:
        svc = AlertService(db)
        outcomes = await svc.retry_failed_alerts(limit=limit)
        await db.commit()

    retried = len(outcomes)
    recovered = sum(1 for o in outcomes if o.get("status") == "ALERTED")
    still_failed = sum(1 for o in outcomes if o.get("status") == "ALERTED_FAILED")

    logger.info(
        "retry_alerts_done",
        retried=retried,
        recovered=recovered,
        still_failed=still_failed,
    )
    if outcomes:
        for o in outcomes:
            logger.info("retry_alert_outcome", **o)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retry failed Aero-Flare alerts")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of ALERTED_FAILED events to retry (default: 50)",
    )
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))
