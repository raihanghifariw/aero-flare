"""
Celery application instance and configuration for Aero-Flare.
Handles distributed background jobs and scheduled tasks (Celery Beat).
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL or "redis://localhost:6379/0"
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL or "redis://localhost:6379/0"

celery_app = Celery(
    "aeroflare",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
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
    beat_schedule={
        "periodic-firms-ingestion": {
            "task": "tasks.ingest_firms",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "kwargs": {"source": "scheduled_beat"},
        },
    },
)
