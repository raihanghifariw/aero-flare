"""
Health check endpoint — no authentication required.
Returns system status: DB connectivity, Ollama reachability, last ingestion timestamp.
FR-18: REST API availability check.

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
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


@router.get(
    "/health",
    summary="System health check",
    response_description="Health status of all system components",
)
@limiter.limit("60/minute")
async def health_check(request: Request) -> JSONResponse:  # request required by slowapi
    """
    Returns the health status of the Aero-Flare backend.
    Checks: database connectivity, Ollama VLM reachability.
    No authentication required.
    """
    settings = get_settings()
    status: dict[str, Any] = {
        "status": "healthy",
        "version": VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {},
    }
    overall_healthy = True

    # --- Database check ---
    db_start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["components"]["database"] = {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 1),
        }
    except Exception as e:
        logger.error("health_db_check_failed", error=str(e))
        status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # --- Ollama check ---
    ollama_start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
        status["components"]["ollama"] = {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - ollama_start) * 1000, 1),
        }
    except Exception as e:
        logger.warning("health_ollama_check_failed", error=str(e))
        # Ollama being down doesn't make the whole system unhealthy —
        # rule-based fallback covers this. Warn only.
        status["components"]["ollama"] = {
            "status": "degraded",
            "note": "rule-based fallback active",
            "error": str(e),
        }

    if not overall_healthy:
        status["status"] = "unhealthy"

    http_status = 200 if overall_healthy else 503
    return JSONResponse(content=status, status_code=http_status)
