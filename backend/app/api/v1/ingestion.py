"""
Ingestion trigger endpoint — wired to Celery distributed task queue.
POST /api/v1/ingestion/trigger — called by GitHub Actions or admin dashboard.
GET /api/v1/ingestion/status/{job_id} — check status of background ingestion.

NOTE: Do NOT add `from __future__ import annotations` here (breaks slowapi-wrapped endpoints).
"""
from typing import Any

import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.queue import task_queue
from app.core.security import limiter
from app.workers.celery_app import celery_app
from app.workers.tasks import ingest_firms_task

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


@router.post(
    "/trigger",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger FIRMS ingestion pipeline",
    description=(
        "Enqueues FIRMS ingestion into Celery background task queue. "
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
    Trigger the full FIRMS ingestion + triage pipeline via Celery.
    Returns 202 Accepted immediately.
    """
    logger.info("ingestion_trigger_received")
    try:
        celery_task = ingest_firms_task.delay(source="api_trigger")
        job_id = str(celery_task.id)
        logger.info("ingestion_task_dispatched_celery", task_id=job_id)
    except Exception as e:
        logger.warning("celery_dispatch_fallback_to_queue", error=str(e))
        job_id = await task_queue.enqueue("ingest_firms", {"source": "api_trigger"})

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
    # 1. Query Celery AsyncResult
    async_res = AsyncResult(job_id, app=celery_app)
    if async_res.state:
        state = async_res.state
        status_map = {
            "PENDING": "queued",
            "RECEIVED": "queued",
            "STARTED": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "RETRY": "retrying",
            "REVOKED": "cancelled",
        }
        res_data = None
        err_msg = None

        if async_res.successful():
            res_data = async_res.result if isinstance(async_res.result, dict) else {"data": async_res.result}
        elif async_res.failed():
            err_msg = str(async_res.result)

        if state != "PENDING" or async_res.result is not None:
            return JobStatusResponse(
                job_id=job_id,
                task_name="tasks.ingest_firms",
                status=status_map.get(state, state.lower()),
                result=res_data,
                error=err_msg,
            )

    # 2. Check fallback task queue
    job_data = await task_queue.get_job_status(job_id)
    if job_data:
        return JobStatusResponse(
            job_id=job_data["job_id"],
            task_name=job_data.get("task_name", "unknown"),
            status=job_data.get("status", "unknown"),
            enqueued_at=job_data.get("enqueued_at"),
            updated_at=job_data.get("updated_at"),
            result=job_data.get("result"),
            error=job_data.get("error"),
        )

    # If pending in celery without result
    if async_res.state == "PENDING":
        return JobStatusResponse(
            job_id=job_id,
            task_name="tasks.ingest_firms",
            status="queued",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job {job_id} not found",
    )

