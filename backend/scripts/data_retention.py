"""
Data retention script — called by GitHub Actions data_retention.yml every Sunday midnight.
Prunes old R2 tiles and archives old audit log entries.

Usage:
    python backend/scripts/data_retention.py --prune-tiles-days 180 --archive-audit-days 365

Full implementation added by AGENT-10 (Deployment Agent) in Phase 7.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main(prune_tiles_days: int, archive_audit_days: int) -> None:
    from app.core.config import get_settings
    from app.core.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)

    import structlog
    logger = structlog.get_logger()

    logger.info(
        "data_retention_start",
        prune_tiles_days=prune_tiles_days,
        archive_audit_days=archive_audit_days,
    )
    # TODO (AGENT-10): implement R2 tile pruning + audit log archiving
    logger.info("data_retention_stub", note="Full implementation in Phase 7")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prune-tiles-days", type=int, default=180)
    parser.add_argument("--archive-audit-days", type=int, default=365)
    args = parser.parse_args()
    asyncio.run(main(args.prune_tiles_days, args.archive_audit_days))
