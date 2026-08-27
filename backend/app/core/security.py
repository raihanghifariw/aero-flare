"""
Security utilities for the Aero-Flare backend.

Provides:
- `verify_api_key`   — FastAPI Depends()-compatible auth guard (raises 403)
- `limiter`          — slowapi Limiter singleton used in all rate-limit decorators

The `/health` endpoint is exempt from both — it must be reachable by
Railway/Vercel health probes without credentials.
"""
from __future__ import annotations

import structlog
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.schemas.common import get_trace_id

logger = structlog.get_logger()

# ─── Rate limiter singleton ───────────────────────────────────────────────────
# Key function: client IP address.
# Attach to app.state.limiter in main.py so slowapi middleware can find it.
limiter = Limiter(key_func=get_remote_address)

# ─── API key auth ─────────────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    Validates the X-API-Key request header.

    Raises:
        403 FORBIDDEN — if the key is absent or does not match settings.API_KEY.

    Returns:
        The valid API key string (useful for logging in the calling handler).

    Exempt endpoints:
        /health and /metrics — register those routers WITHOUT this dependency.
    """
    settings = get_settings()
    if not api_key or api_key != settings.API_KEY:
        logger.warning(
            "api_key_rejected",
            prefix=api_key[:4] if api_key else "none",
            trace_id=get_trace_id(),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": "Invalid or missing API key",
                "trace_id": get_trace_id(),
            },
        )
    return api_key
