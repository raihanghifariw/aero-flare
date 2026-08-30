"""
Distributed Cache Service with Redis and In-Memory Graceful Fallback.
Provides low-latency sub-millisecond caching for high-traffic API routes,
aggregated stats, and external API responses (Open-Meteo weather).
"""
from __future__ import annotations

import asyncio
import functools
import json
import time
from collections.abc import Callable
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class CacheService:
    """
    Async Cache Service with Redis connection pooling and automatic
    in-memory dictionary fallback when Redis is offline or disabled.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._in_memory_store: dict[str, tuple[Any, float]] = {}
        self._redis_available: bool | None = None

    async def _get_client(self) -> aioredis.Redis | None:
        settings = get_settings()
        if not settings.CACHE_ENABLED or not settings.REDIS_URL:
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
                self._redis_available = True
                safe_host = settings.REDIS_URL.split("@")[-1]
                logger.info("redis_cache_connected", host=safe_host)
            except Exception as e:
                logger.warning("redis_cache_unavailable_using_fallback", error=str(e))
                self._redis_available = False
                self._redis = None

        return self._redis


    async def get(self, key: str) -> Any | None:
        """Retrieve a value from Redis or in-memory fallback store."""
        client = await self._get_client()
        if client is not None:
            try:
                raw = await client.get(key)
                if raw is not None:
                    return json.loads(raw)
                return None
            except Exception as e:
                logger.warning("redis_get_failed_fallback", key=key, error=str(e))

        # In-memory fallback
        item = self._in_memory_store.get(key)
        if item is not None:
            value, expire_at = item
            if time.time() < expire_at:
                return value
            del self._in_memory_store[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Store a value in Redis or in-memory store with TTL in seconds."""
        client = await self._get_client()
        serialized = json.dumps(value, default=str)

        if client is not None:
            try:
                await client.set(key, serialized, ex=ttl)
                return True
            except Exception as e:
                logger.warning("redis_set_failed_fallback", key=key, error=str(e))

        # In-memory fallback
        expire_at = time.time() + ttl
        self._in_memory_store[key] = (value, expire_at)
        return True

    async def delete(self, key: str) -> bool:
        """Delete a single cache key."""
        client = await self._get_client()
        if client is not None:
            try:
                await client.delete(key)
            except Exception as e:
                logger.warning("redis_delete_failed", key=key, error=str(e))

        self._in_memory_store.pop(key, None)
        return True

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob-like pattern (e.g. 'events:*').
        Used for atomic cache invalidation after data mutations.
        """
        deleted_count = 0
        client = await self._get_client()

        if client is not None:
            try:
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    deleted_count = await client.delete(*keys)
            except Exception as e:
                logger.warning("redis_delete_pattern_failed", pattern=pattern, error=str(e))

        # Clean in-memory store matching pattern
        import fnmatch
        to_del = [k for k in self._in_memory_store if fnmatch.fnmatch(k, pattern)]
        for k in to_del:
            self._in_memory_store.pop(k, None)
            deleted_count += 1

        logger.info("cache_invalidated", pattern=pattern, count=deleted_count)
        return deleted_count

    async def close(self) -> None:
        """Close connection pool cleanly."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


# Singleton instance
cache = CacheService()


def cached(ttl: int = 60, prefix: str = "cache") -> Callable:
    """
    FastAPI async endpoint / method decorator for automatic transparent caching.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name and primitive kwargs
            cache_args = [str(a) for a in args if isinstance(a, (str, int, float, bool))]
            cache_kwargs = [f"{k}={v}" for k, v in sorted(kwargs.items()) if isinstance(v, (str, int, float, bool))]
            key_suffix = ":".join(cache_args + cache_kwargs) or "default"
            cache_key = f"{prefix}:{func.__name__}:{key_suffix}"

            cached_val = await cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)
            if result is not None:
                # Handle Pydantic models / lists of models
                if hasattr(result, "model_dump"):
                    to_cache = result.model_dump(mode="json")
                elif isinstance(result, list) and result and hasattr(result[0], "model_dump"):
                    to_cache = [item.model_dump(mode="json") for item in result]
                elif isinstance(result, dict):
                    to_cache = result
                else:
                    to_cache = result

                await cache.set(cache_key, to_cache, ttl=ttl)

            return result
        return wrapper
    return decorator
