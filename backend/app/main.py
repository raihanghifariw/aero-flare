"""
Aero-Flare Backend — FastAPI Application Entry Point
All routers mounted; security middleware configured; telemetry active.
FR-18: REST API with versioned endpoints.
FR-20: OpenAPI docs at /docs.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import limiter

logger = structlog.get_logger()

# API key security scheme for Swagger UI autodoc
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)
    logger.info("aero_flare_starting", environment=settings.ENVIRONMENT, version="1.0.0")
    yield
    logger.info("aero_flare_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Aero-Flare API",
        version="1.0.0",
        description=(
            "Early wildfire detection and triage system for Indonesia. "
            "Processes NASA FIRMS hotspot data, runs VLM triage via Ollama, "
            "predicts fire spread with XGBoost, and dispatches real-time alerts."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Rate limiting (slowapi) ---
    # limiter instance lives in app.state so slowapi middleware can find it
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # --- HTTPS redirect in production ---
    if settings.ENVIRONMENT == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    # --- CORS ---
    allowed_origins = (
        ["https://aero-flare.vercel.app"]
        if settings.ENVIRONMENT == "production"
        else ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    # --- Request timing ---
    from collections.abc import Awaitable, Callable
    from fastapi.responses import Response

    @app.middleware("http")
    async def add_process_time(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = str(
            round((time.perf_counter() - start) * 1000, 2)
        )
        return response

    # --- Routers ---
    from app.api.v1.router import router as v1_router
    app.include_router(v1_router, prefix="/api/v1")

    # --- Telemetry (OTel + Prometheus) ---
    from app.core.telemetry import setup_telemetry
    setup_telemetry(app)

    # --- Global exception handler ---
    from app.schemas.common import get_trace_id

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            trace_id=get_trace_id(),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "trace_id": get_trace_id(),
            },
        )

    return app


app = create_app()
