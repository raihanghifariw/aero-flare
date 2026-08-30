"""
Helper test script to verify Redis Cache and TaskQueue connectivity.

Usage:
    python backend/scripts/test_redis.py
"""
import asyncio
import os
import sys

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.cache import cache
from app.core.queue import task_queue


async def main() -> None:
    print("--------------------------------------------------")
    print("Testing Aero-Flare Redis Cache & Task Queue System")
    print("--------------------------------------------------")

    # 1. Test Cache Set & Get
    await cache.set("ping", "pong", 60)
    result = await cache.get("ping")
    print("1. Cache Test (Key 'ping'):", result)
    assert result == "pong", "Cache result did not match expected value"

    # 2. Test Task Queue Enqueue & Status Check
    job_id = await task_queue.enqueue("test_job", {"test_param": "aero_flare"})
    status_record = await task_queue.get_job_status(job_id)
    status_val = status_record["status"] if status_record else "unknown"
    print("2. Task Queue Test (Job ID):", job_id, "| Status:", status_val)
    assert status_val == "queued", "Job status should be queued"

    # 3. Clean up
    await cache.close()
    await task_queue.close()
    print("--------------------------------------------------")
    print("SUCCESS: Redis Cache and Task Queue are working!")
    print("--------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
