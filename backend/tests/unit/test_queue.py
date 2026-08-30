"""
Unit tests for the asynchronous TaskQueue and Worker subsystem (queue.py).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.queue import TaskQueue


@pytest.mark.asyncio
async def test_task_queue_in_memory_enqueue_and_pop() -> None:
    queue = TaskQueue()
    with patch.object(queue, "_get_client", return_value=None):
        job_id = await queue.enqueue("test_task", {"param": 123})
        assert job_id.startswith("job_")

        status = await queue.get_job_status(job_id)
        assert status is not None
        assert status["status"] == "queued"
        assert status["payload"] == {"param": 123}

        # Pop from queue
        popped = await queue.pop_job(timeout=1)
        assert popped is not None
        assert popped["job_id"] == job_id
        assert popped["task_name"] == "test_task"


@pytest.mark.asyncio
async def test_task_queue_update_status() -> None:
    queue = TaskQueue()
    with patch.object(queue, "_get_client", return_value=None):
        job_id = await queue.enqueue("status_task", {"value": "init"})
        await queue.update_job_status(job_id, "running")

        s1 = await queue.get_job_status(job_id)
        assert s1 is not None
        assert s1["status"] == "running"

        await queue.update_job_status(job_id, "completed", result={"success": True})
        s2 = await queue.get_job_status(job_id)
        assert s2 is not None
        assert s2["status"] == "completed"
        assert s2["result"] == {"success": True}
