"""
Health check endpoint — no authentication required.
Returns system status: DB connectivity, Ollama reachability, last ingestion timestamp.
FR-18: REST API availability check.

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import asyncio
import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import limiter
from app.models.base import AsyncSessionLocal

router = APIRouter(tags=["health"])
logger = structlog.get_logger()

VERSION = "1.0.0"

# In-memory health cache to prevent hammering remote databases on high-frequency polling
_HEALTH_CACHE_TTL_SECONDS = 5.0
_cached_health_status: dict[str, Any] | None = None
_cached_http_status: int = 200
_last_health_check_time: float = 0.0


async def _check_database() -> dict[str, Any]:
    """Check database connectivity and measure query latency."""
    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as e:
        logger.error("health_db_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


async def _check_ollama(base_url: str) -> dict[str, Any]:
    """Check Ollama VLM availability with a fast timeout."""
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
        return {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as e:
        logger.warning("health_ollama_check_failed", error=str(e))
        return {
            "status": "degraded",
            "note": "rule-based fallback active",
            "error": str(e),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


@router.get(
    "/health",
    summary="System health check",
    response_description="Health status of all system components",
)
@limiter.limit("120/minute")
async def health_check(request: Request) -> JSONResponse:
    """
    Returns the health status of the Aero-Flare backend.
    Checks: database connectivity and Ollama VLM reachability concurrently.
    Cached for 5s to eliminate latency spikes under high-frequency polling.
    """
    global _cached_health_status, _cached_http_status, _last_health_check_time

    now = time.perf_counter()
    if _cached_health_status is not None and (now - _last_health_check_time) < _HEALTH_CACHE_TTL_SECONDS:
        return JSONResponse(content=_cached_health_status, status_code=_cached_http_status)

    settings = get_settings()

    # Execute DB and Ollama health checks concurrently in parallel
    db_result, ollama_result = await asyncio.gather(
        _check_database(),
        _check_ollama(settings.OLLAMA_BASE_URL),
        return_exceptions=False,
    )

    overall_healthy = db_result.get("status") == "healthy"

    status = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "version": VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": db_result,
            "ollama": ollama_result,
        },
    }

    http_status = 200 if overall_healthy else 503

    # Update cache
    _cached_health_status = status
    _cached_http_status = http_status
    _last_health_check_time = now

    return JSONResponse(content=status, status_code=http_status)
