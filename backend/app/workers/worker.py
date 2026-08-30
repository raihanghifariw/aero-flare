"""
Aero-Flare Background Worker CLI entrypoint.
Can run Celery worker or standalone async queue consumer.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.queue import task_queue
from app.workers.celery_app import celery_app
from app.workers.tasks import _async_ingest_firms, _async_process_event

logger = structlog.get_logger()

MAX_CONCURRENT_TASKS = 6


async def handle_job(job: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    """Execute a popped job with status tracking and concurrency semaphore."""
    async with semaphore:
        job_id = job["job_id"]
        task_name = job["task_name"]
        payload = job.get("payload", {})

        logger.info("worker_executing_job", job_id=job_id, task=task_name)
        await task_queue.update_job_status(job_id, "running")

        try:
            if task_name == "process_event":
                result = await _async_process_event(payload["event_id"])
            elif task_name == "ingest_firms":
                result = await _async_ingest_firms(payload.get("source", "manual"))
            else:
                raise ValueError(f"Unknown task name: {task_name}")

            await task_queue.update_job_status(job_id, "completed", result=result)
            logger.info("worker_job_completed", job_id=job_id, task=task_name)
        except Exception as exc:
            logger.error("worker_job_failed", job_id=job_id, task=task_name, error=str(exc))
            await task_queue.update_job_status(job_id, "failed", error=str(exc))


def run_celery_worker() -> None:
    """Entrypoint to run Celery worker CLI."""
    argv = ["worker", "--loglevel=info"]
    celery_app.worker_main(argv)


if __name__ == "__main__":
    run_celery_worker()
