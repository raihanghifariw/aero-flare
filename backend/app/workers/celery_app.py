"""
Celery application instance and configuration for Aero-Flare.
Handles distributed background jobs and scheduled tasks (Celery Beat).
"""
from __future__ import annotations

import os
import ssl

# Clean up malformed CELERY_* env vars (e.g. literal 'REDIS_URL') before Celery parses them
for env_key in ("CELERY_RESULT_BACKEND", "CELERY_BROKER_URL", "CELERY_BACKEND"):
    val = os.environ.get(env_key, "").strip().strip("'\"")
    if val and ("://" not in val or val in {"REDIS_URL", "${REDIS_URL}", "$REDIS_URL", "none", "None"}):
        os.environ.pop(env_key, None)

from celery import Celery  # noqa: E402
from celery.schedules import crontab  # noqa: E402

from app.core.config import get_settings  # noqa: E402

settings = get_settings()



def _sanitize_url(url: str | None, fallback: str) -> str:
    """Sanitize URL to prevent literal env var names from being parsed as module names."""
    if not url or "://" not in url or url in {"REDIS_URL", "${REDIS_URL}", "$REDIS_URL"}:
        return fallback
    return url


base_redis = settings.REDIS_URL if "://" in settings.REDIS_URL else "redis://localhost:6379/0"
broker_url = _sanitize_url(settings.CELERY_BROKER_URL, fallback=base_redis)
result_backend = _sanitize_url(settings.CELERY_RESULT_BACKEND, fallback=broker_url)

celery_app = Celery(
    "aeroflare",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"],
)

ssl_options = (
    {"ssl_cert_reqs": ssl.CERT_NONE}
    if (broker_url.startswith("rediss://") or result_backend.startswith("rediss://"))
    else None
)

celery_app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    result_expires=86400,  # 24 hours
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    beat_schedule={
        "periodic-firms-ingestion": {
            "task": "tasks.ingest_firms",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "kwargs": {"source": "scheduled_beat"},
        },
    },
)
