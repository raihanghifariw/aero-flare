"""
Ingestion trigger endpoint — wired to distributed task queue (Scalable Architecture).
POST /api/v1/ingestion/trigger — called by GitHub Actions or admin dashboard.
GET /api/v1/ingestion/status/{job_id} — check status of background ingestion.

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.queue import task_queue
from app.core.security import limiter

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = structlog.get_logger()


class IngestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    job_id: str | None = None
    status: str = "queued"


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str
    task_name: str
    status: str
    enqueued_at: float | None = None
    updated_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


async def _drain_in_memory_queue() -> None:
    """Drain in-memory queue if no external worker process is consuming."""
    from app.workers.worker import handle_job
    semaphore = asyncio.Semaphore(4)
    while True:
        job = await task_queue.pop_job(timeout=1)
        if not job:
            break
        await handle_job(job, semaphore)


@router.post(
    "/trigger",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger FIRMS ingestion pipeline",
    description=(
        "Enqueues FIRMS ingestion into the background task queue. "
        "Returns 202 immediately with job_id for status tracking."
    ),
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("30/minute")
async def trigger_ingestion(
    request: Request,  # required by slowapi
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Trigger the full FIRMS ingestion + triage pipeline via TaskQueue.
    Returns 202 Accepted immediately.
    """
    logger.info("ingestion_trigger_received")
    job_id = await task_queue.enqueue("ingest_firms", {"source": "api_trigger"})

    # Ensure background worker processing for in-memory fallback
    background_tasks.add_task(_drain_in_memory_queue)

    return IngestionResponse(
        message="Ingestion pipeline queued successfully.",
        job_id=job_id,
        status="queued",
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get status of an ingestion or processing job",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("60/minute")
async def get_ingestion_job_status(
    request: Request,
    job_id: str,
) -> JobStatusResponse:
    """Check progress and result of a background ingestion job."""
    job_data = await task_queue.get_job_status(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(
        job_id=job_data["job_id"],
        task_name=job_data.get("task_name", "unknown"),
        status=job_data.get("status", "unknown"),
        enqueued_at=job_data.get("enqueued_at"),
        updated_at=job_data.get("updated_at"),
        result=job_data.get("result"),
        error=job_data.get("error"),
    )
