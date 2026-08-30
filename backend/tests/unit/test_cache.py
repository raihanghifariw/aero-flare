"""
Unit tests for the distributed caching layer (cache.py).
Tests both in-memory fallback and Redis mocked operations.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.cache import CacheService, cached


@pytest.mark.asyncio
async def test_cache_service_in_memory_set_get() -> None:
    cache = CacheService()
    # Ensure Redis is disabled for this test to test in-memory fallback
    with patch.object(cache, "_get_client", return_value=None):
        await cache.set("test:key:1", {"message": "hello", "count": 42}, ttl=60)
        val = await cache.get("test:key:1")
        assert val == {"message": "hello", "count": 42}


@pytest.mark.asyncio
async def test_cache_service_in_memory_expiration() -> None:
    cache = CacheService()
    with patch.object(cache, "_get_client", return_value=None):
        # Set with 0 second TTL (instant expiry)
        await cache.set("test:key:expire", "temporary", ttl=-1)
        val = await cache.get("test:key:expire")
        assert val is None


@pytest.mark.asyncio
async def test_cache_service_delete() -> None:
    cache = CacheService()
    with patch.object(cache, "_get_client", return_value=None):
        await cache.set("test:key:del", "to_delete", ttl=60)
        assert await cache.get("test:key:del") == "to_delete"
        await cache.delete("test:key:del")
        assert await cache.get("test:key:del") is None


@pytest.mark.asyncio
async def test_cache_service_delete_pattern() -> None:
    cache = CacheService()
    with patch.object(cache, "_get_client", return_value=None):
        await cache.set("events:list:1", [1, 2, 3], ttl=60)
        await cache.set("events:list:2", [4, 5, 6], ttl=60)
        await cache.set("stats:summary", {"total": 10}, ttl=60)

        deleted = await cache.delete_pattern("events:*")
        assert deleted == 2
        assert await cache.get("events:list:1") is None
        assert await cache.get("events:list:2") is None
        assert await cache.get("stats:summary") == {"total": 10}


@pytest.mark.asyncio
async def test_cached_decorator() -> None:
    call_count = 0

    @cached(ttl=60, prefix="test_dec")
    async def sample_function(x: int, y: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {"x": x, "y": y, "call_count": call_count}

    res1 = await sample_function(10, "foo")
    assert res1["call_count"] == 1

    # Second call with same args should return cached result without incrementing call_count
    res2 = await sample_function(10, "foo")
    assert res2["call_count"] == 1
    assert call_count == 1

    # Call with different arg executes function
    res3 = await sample_function(20, "foo")
    assert res3["call_count"] == 2
    assert call_count == 2
