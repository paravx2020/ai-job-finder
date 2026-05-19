"""Disk-based cache for AI API responses.

Caches AI improvement results keyed by SHA256 hash of (prompt + model + section).
Uses JSON files stored in data/cache/ with TTL-based expiry.

Usage:
    from src.utils.cache import cached_ai_call

    @cached_ai_call(ttl=86400)
    def call_ai(prompt: str, model: str, section: str) -> str:
        # ... actual API call ...
        return response
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Manages disk-based cache entries for AI responses."""

    def __init__(self, cache_dir: str | Path | None = None, enabled: bool = True) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).resolve().parent.parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self._hits = 0
        self._misses = 0

    @staticmethod
    def hash_prompt(prompt: str, model: str, section: str) -> str:
        """Generate a SHA256 cache key from prompt, model, and section."""
        key_str = f"{model}:{section}:{prompt}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        """Retrieve a cached response if it exists and hasn't expired.

        Args:
            key: SHA256 hash of the cache key.

        Returns:
            Cached response string, or None if not found/expired.
        """
        if not self.enabled:
            return None

        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                entry = json.load(f)

            # Check TTL expiry
            if time.time() - entry["created_at"] > entry["ttl"]:
                logger.debug("Cache entry expired: %s", key[:12])
                cache_file.unlink()
                self._misses += 1
                return None

            self._hits += 1
            logger.debug("Cache hit: %s", key[:12])
            return entry["response"]

        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning("Cache read error for %s: %s", key[:12], e)
            self._misses += 1
            return None

    def set(self, key: str, response: str, model: str, ttl: int = 86400) -> None:
        """Store a response in the cache.

        Args:
            key: SHA256 hash of the cache key.
            response: The AI response to cache.
            model: The AI model used.
            ttl: Time-to-live in seconds (default: 24 hours).
        """
        if not self.enabled:
            return

        cache_file = self.cache_dir / f"{key}.json"
        entry = {
            "key": key,
            "response": response,
            "model": model,
            "section": key.split(":")[1] if ":" in key else "",
            "created_at": time.time(),
            "ttl": ttl,
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            logger.debug("Cache stored: %s", key[:12])
        except OSError as e:
            logger.warning("Cache write error for %s: %s", key[:12], e)

    def clear(self) -> int:
        """Clear all cached entries. Returns number of files removed."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass
        logger.info("Cache cleared: %d entries removed", count)
        return count

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        # Count actual files on disk
        file_count = len(list(self.cache_dir.glob("*.json")))

        # Calculate total size
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json") if f.is_file())

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 1),
            "entries_on_disk": file_count,
            "disk_size_bytes": total_size,
            "enabled": self.enabled,
        }


# ── Module-level singleton ──────────────────────────────────────────────────

_cache: CacheManager | None = None


def get_cache_manager(
    cache_dir: str | Path | None = None,
    enabled: bool = True,
) -> CacheManager:
    """Get or create the global cache manager instance.

    Args:
        cache_dir: Override default cache directory.
        enabled: Whether caching is enabled.

    Returns:
        The global CacheManager instance.
    """
    global _cache
    if _cache is None:
        _cache = CacheManager(cache_dir=cache_dir, enabled=enabled)
    return _cache


def reset_cache_manager() -> None:
    """Reset the global cache manager (useful for testing)."""
    global _cache
    _cache = None


# ── Decorator for caching AI calls ──────────────────────────────────────────

def cached_ai_call(ttl: int = 86400) -> Callable:
    """Decorator that caches AI API responses.

    The decorated function must accept at least these keyword arguments:
    - prompt: str
    - model: str
    - section: str

    Usage:
        @cached_ai_call(ttl=86400)
        def call_ai(prompt: str, model: str, section: str) -> str:
            # actual API call
            return response

    Args:
        ttl: Cache time-to-live in seconds (default: 24 hours).

    Returns:
        Decorated function with caching.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> str:
            cache = get_cache_manager()

            # Extract cache key components
            prompt = kwargs.get("prompt", "")
            model = kwargs.get("model", "")
            section = kwargs.get("section", "")

            key = CacheManager.hash_prompt(prompt, model, section)

            # Try cache first
            cached = cache.get(key)
            if cached is not None:
                logger.info("Using cached AI response for section: %s", section)
                return cached

            # Cache miss — call the actual function
            logger.info("Calling AI API for section: %s", section)
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(key, result, model=model, ttl=ttl)

            return result
        return wrapper
    return decorator
