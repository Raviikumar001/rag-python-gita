# app/services/cache.py
import asyncio
import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional

import redis.asyncio as redis


class CacheService(ABC):
    """Abstract cache interface supporting both Redis and in-memory backends."""

    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class MemoryCache(CacheService):
    """Thread-safe in-memory LRU cache with TTL support."""

    def __init__(self, maxsize: int = 1000):
        self._cache: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        async with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if expiry is not None and time.time() > expiry:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        async with self._lock:
            expiry = time.time() + ttl if ttl else None
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def close(self) -> None:
        async with self._lock:
            self._cache.clear()


class RedisCache(CacheService):
    """Async Redis cache backend."""

    def __init__(self, url: str):
        self._redis = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any:
        value = await self._redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.close()


def create_cache(redis_url: Optional[str] = None) -> CacheService:
    if redis_url:
        return RedisCache(redis_url)
    return MemoryCache()
