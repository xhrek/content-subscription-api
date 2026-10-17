"""Redis cache + rate-limit store with graceful in-memory fallback."""
import json
import logging
import threading
import time
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, url: str | None) -> None:
        self._url = url
        self._client: redis.Redis | None = None
        self._initialized = False
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[float, int]] = {}

    @property
    def client(self) -> redis.Redis | None:
        if not self._initialized:
            self._initialized = True
            if self._url:
                try:
                    c = redis.Redis.from_url(
                        self._url, decode_responses=True,
                        socket_connect_timeout=1, socket_timeout=1,
                    )
                    c.ping()
                    self._client = c
                except redis.RedisError:
                    logger.warning("Redis unavailable; caching disabled, using in-memory rate limiting")
        return self._client

    def get(self, key: str) -> Any | None:
        if not self.client:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except redis.RedisError:
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self.client:
            return
        try:
            self.client.setex(key, ttl or settings.CACHE_TTL_SECONDS, json.dumps(value, default=str))
        except redis.RedisError:
            pass

    def invalidate(self, prefix: str) -> None:
        if not self.client:
            return
        try:
            keys = list(self.client.scan_iter(match=f"{prefix}*", count=500))
            if keys:
                self.client.delete(*keys)
        except redis.RedisError:
            pass

    def hit(self, key: str, window: int) -> tuple[int, int]:
        """Increment a fixed-window counter. Returns (count, seconds_until_reset)."""
        if self.client:
            try:
                pipe = self.client.pipeline()
                pipe.incr(key)
                pipe.expire(key, window, nx=True)
                pipe.ttl(key)
                count, _, ttl = pipe.execute()
                return int(count), max(int(ttl), 0)
            except redis.RedisError:
                pass
        now = time.time()
        with self._lock:
            start, count = self._counters.get(key, (now, 0))
            if now - start >= window:
                start, count = now, 0
            count += 1
            self._counters[key] = (start, count)
            return count, int(window - (now - start))

    def reset_local(self) -> None:
        with self._lock:
            self._counters.clear()


cache = Cache(settings.REDIS_URL)
