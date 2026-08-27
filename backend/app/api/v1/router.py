"""
API v1 router — assembles all sub-routers under /api/v1
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import alerts, events, health, ingestion, predictions, stats, tiles, triage, webhooks

router = APIRouter()

router.include_router(health.router)
router.include_router(events.router)
router.include_router(triage.router)
router.include_router(predictions.router)
router.include_router(stats.router)
router.include_router(webhooks.router)
router.include_router(ingestion.router)
router.include_router(alerts.router)
router.include_router(tiles.router)
