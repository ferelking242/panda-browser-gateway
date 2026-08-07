"""
Response cache — in-memory TTL cache for chat completions.

Controlled by Config.CACHE_TTL (seconds). 0 = disabled.
Key = SHA-256 of (provider, model, messages content).
Thread-safe with asyncio.Lock.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from src.config import Config
from src.log import setup_logging

log = setup_logging("cache")


class ResponseCache:
    """In-memory response cache with TTL eviction."""

    def __init__(self, ttl: int = 0) -> None:
        self._ttl = ttl
        # key → (response_object, expires_at)
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    # ── Properties ───────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._ttl > 0

    # ── Cache key ────────────────────────────────────────────────

    def _make_key(self, provider: str, model: str, messages: list) -> str:
        payload = json.dumps(
            {
                "provider": provider,
                "model": model,
                "messages": [
                    {"role": m.role, "content": str(m.content)}
                    for m in messages
                ],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    # ── Public API ───────────────────────────────────────────────

    async def get(self, provider: str, model: str, messages: list) -> Any | None:
        """Return cached response or None on miss/expired."""
        if not self.enabled:
            return None
        key = self._make_key(provider, model, messages)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                self._misses += 1
                log.debug(f"Cache EXPIRED — key={key[:12]}")
                return None
            self._hits += 1
            log.info(f"Cache HIT — key={key[:12]}... ({self._hits} hits total)")
            return value

    async def set(self, provider: str, model: str, messages: list, response: Any) -> None:
        """Store a response in the cache."""
        if not self.enabled:
            return
        key = self._make_key(provider, model, messages)
        async with self._lock:
            self._store[key] = (response, time.time() + self._ttl)
            # Evict expired entries opportunistically (max scan = 100)
            if len(self._store) > 1000:
                now = time.time()
                expired_keys = [
                    k for k, (_, exp) in list(self._store.items())[:200]
                    if exp <= now
                ]
                for k in expired_keys:
                    del self._store[k]
            log.debug(f"Cache SET — key={key[:12]}..., ttl={self._ttl}s, entries={len(self._store)}")

    async def clear(self) -> int:
        """Flush all entries. Returns count removed."""
        async with self._lock:
            count = len(self._store)
            self._store.clear()
            self._hits = 0
            self._misses = 0
            log.info(f"Cache CLEARED — removed {count} entries")
            return count

    def stats(self) -> dict:
        now = time.time()
        valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        total = self._hits + self._misses
        hit_rate = round(self._hits / total * 100, 1) if total else 0.0
        return {
            "enabled": self.enabled,
            "ttl_seconds": self._ttl,
            "entries_total": len(self._store),
            "entries_valid": valid,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": hit_rate,
        }


# ── Module-level singleton ───────────────────────────────────────

_cache: ResponseCache | None = None


def get_cache() -> ResponseCache:
    global _cache
    if _cache is None:
        _cache = ResponseCache(ttl=Config.CACHE_TTL)
    return _cache


def init_cache() -> ResponseCache:
    global _cache
    _cache = ResponseCache(ttl=Config.CACHE_TTL)
    log.info(
        f"Response cache initialized — ttl={Config.CACHE_TTL}s, "
        f"enabled={_cache.enabled}"
    )
    return _cache
