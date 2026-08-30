"""
Asynchronous Task Queue Dispatcher for Aero-Flare.
Supports Redis-backed distributed task queuing with automatic
transparent in-memory background task fallback for local development & testing.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

QUEUE_KEY = "aeroflare:tasks:default"
JOB_STATUS_PREFIX = "aeroflare:job:"


class TaskQueue:
    """
    Async Task Queue for dispatching background jobs to distributed Redis workers.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._in_memory_jobs: dict[str, dict[str, Any]] = {}
        self._in_memory_queue: asyncio.Queue[dict[str, Any]] | None = None

    def _get_in_memory_queue(self) -> asyncio.Queue[dict[str, Any]]:
        if self._in_memory_queue is None:
            self._in_memory_queue = asyncio.Queue()
        return self._in_memory_queue

    async def _get_client(self) -> aioredis.Redis | None:

        settings = get_settings()
        if not settings.QUEUE_ENABLED or not settings.REDIS_URL:
            return None

        current_loop = asyncio.get_running_loop()
        if self._redis is not None and self._loop != current_loop:
            self._redis = None

        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=3.0,
                )
                await self._redis.ping()
                self._loop = current_loop
            except Exception as e:
                logger.warning("redis_queue_unavailable_using_fallback", error=str(e))
                self._redis = None

        return self._redis


    async def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        """
        Enqueue a job to the background worker pool.
        Returns unique job_id.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job_record = {
            "job_id": job_id,
            "task_name": task_name,
            "payload": payload,
            "status": "queued",
            "enqueued_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": None,
        }

        client = await self._get_client()
        if client is not None:
            try:
                raw = json.dumps(job_record, default=str)
                # Store job metadata with 24h TTL
                await client.set(f"{JOB_STATUS_PREFIX}{job_id}", raw, ex=86400)
                # Push job to work queue
                await client.lpush(QUEUE_KEY, raw)
                logger.info("job_enqueued_redis", job_id=job_id, task=task_name)
                return job_id
            except Exception as e:
                logger.warning("redis_enqueue_failed_using_memory", error=str(e))

        # In-memory queue fallback
        self._in_memory_jobs[job_id] = job_record
        await self._get_in_memory_queue().put(job_record)
        logger.info("job_enqueued_in_memory", job_id=job_id, task=task_name)
        return job_id

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Fetch current status and result of a background job."""
        client = await self._get_client()
        if client is not None:
            try:
                raw = await client.get(f"{JOB_STATUS_PREFIX}{job_id}")
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning("redis_get_job_status_failed", error=str(e))

        return self._in_memory_jobs.get(job_id)

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Update job state (running, completed, failed)."""
        client = await self._get_client()
        job = await self.get_job_status(job_id) or {}
        job.update({
            "status": status,
            "updated_at": time.time(),
            "result": result,
            "error": error,
        })
        raw = json.dumps(job, default=str)

        if client is not None:
            try:
                await client.set(f"{JOB_STATUS_PREFIX}{job_id}", raw, ex=86400)
            except Exception as e:
                logger.warning("redis_update_job_failed", error=str(e))

        self._in_memory_jobs[job_id] = job

    async def pop_job(self, timeout: int = 2) -> dict[str, Any] | None:
        """Pop a job from Redis queue (or in-memory queue)."""
        client = await self._get_client()
        if client is not None:
            try:
                item = await client.brpop(QUEUE_KEY, timeout=timeout)
                if item:
                    _, raw = item
                    return json.loads(raw)
            except Exception as e:
                logger.warning("redis_pop_job_failed", error=str(e))

        try:
            return await asyncio.wait_for(self._get_in_memory_queue().get(), timeout=float(timeout))
        except (asyncio.TimeoutError, TimeoutError):
            return None


    async def close(self) -> None:
        """Close connection pool cleanly."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


# Singleton instance
task_queue = TaskQueue()

