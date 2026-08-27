"""
Structured logging setup using structlog + JSON formatting.
All logs include: timestamp, level, service, event, trace_id.
"""
from __future__ import annotations

import logging
import sys

import structlog

SERVICE_NAME = "aero-flare-backend"


def add_service_name(
    logger: object,  # noqa: ARG001
    method: str,  # noqa: ARG001
    event_dict: dict,
) -> dict:
    """
    structlog processor: stamp every log entry with the service name.

    NOTE: `structlog.stdlib.add_logger_name` cannot be used here — it reads
    `logger.name`, which only exists on stdlib loggers. This app uses
    `PrintLoggerFactory`, whose `PrintLogger` has no `.name` attribute and
    would raise AttributeError on the first log call (app startup crash).
    """
    event_dict.setdefault("service", SERVICE_NAME)
    return event_dict


def scrub_secrets(
    logger: object,  # noqa: ARG001
    method: str,  # noqa: ARG001
    event_dict: dict,
) -> dict:
    """
    structlog processor: redact known secret field names from log entries.
    Prevents accidental leakage of API keys via logs.
    """
    secret_keys = {
        "api_key", "API_KEY", "secret", "SECRET_KEY",
        "password", "token", "TELEGRAM_BOT_TOKEN",
        "SUPABASE_SERVICE_KEY", "CLOUDFLARE_R2_SECRET",
        "GRAFANA_API_TOKEN", "FIRMS_API_KEY",
        "authorization", "Authorization",
    }
    for key in secret_keys:
        if key in event_dict:
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(environment: str = "development") -> None:
    """Configure structlog for JSON (production) or pretty-print (development)."""

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        add_service_name,
        structlog.processors.TimeStamper(fmt="iso"),
        scrub_secrets,
        structlog.processors.StackInfoRenderer(),
    ]

    if environment == "production":
        # JSON output for log aggregators (Grafana Loki, etc.)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-friendly colored output for local dev
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so uvicorn / sqlalchemy logs flow through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if environment != "production" else logging.INFO,
    )
