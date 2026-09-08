
from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

from gateway.config import CacheConfig


def make_key(messages: list[dict], provider_name: str) -> str:
    payload = json.dumps({"messages": messages, "provider": provider_name}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class MemoryCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: dict) -> None:
        self._store[key] = (time.time() + self.ttl, value)


class RedisCache:
    """Stub — implement with redis.asyncio when you're ready to scale past
    one process. Same get/set interface as MemoryCache so router code never
    needs to change.
    """

    def __init__(self, redis_url: str, ttl_seconds: int):
        raise NotImplementedError(
            "RedisCache is a stub. Install redis.asyncio and implement get/set "
            "against redis_url before setting cache.backend: redis in config.yaml."
        )


def build_cache(config: CacheConfig):
    if config.backend == "redis":
        return RedisCache(config.redis_url, config.ttl_seconds)
    return MemoryCache(config.ttl_seconds)
