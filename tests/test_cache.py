"""Tests for the AI API response cache."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.utils.cache import CacheManager, reset_cache_manager


class TestCacheManager:
    @pytest.fixture(autouse=True)
    def setup(self, temp_dir: Path):
        reset_cache_manager()
        self.cache_dir = temp_dir / "cache"
        self.cache = CacheManager(cache_dir=self.cache_dir)

    def test_hash_is_consistent(self):
        h1 = CacheManager.hash_prompt("test prompt", "gemini-2.0-flash", "summary")
        h2 = CacheManager.hash_prompt("test prompt", "gemini-2.0-flash", "summary")
        assert h1 == h2

    def test_hash_changes_with_input(self):
        h1 = CacheManager.hash_prompt("prompt A", "model1", "summary")
        h2 = CacheManager.hash_prompt("prompt B", "model1", "summary")
        assert h1 != h2

    def test_set_and_get(self):
        key = self.cache.hash_prompt("hello", "model", "test")
        self.cache.set(key, "response", model="model", ttl=60)
        result = self.cache.get(key)
        assert result == "response"

    def test_cache_miss(self):
        result = self.cache.get("nonexistent_key")
        assert result is None

    def test_cache_expiry(self):
        key = self.cache.hash_prompt("hello", "model", "test")
        self.cache.set(key, "response", model="model", ttl=0)  # TTL = 0 means expired immediately
        time.sleep(0.01)  # tiny delay
        result = self.cache.get(key)
        assert result is None  # should be expired

    def test_disabled_cache(self):
        disabled_cache = CacheManager(cache_dir=self.cache_dir, enabled=False)
        key = disabled_cache.hash_prompt("hello", "model", "test")
        disabled_cache.set(key, "response", model="model")
        result = disabled_cache.get(key)
        assert result is None

    def test_clear_cache(self):
        key = self.cache.hash_prompt("hello", "model", "test")
        self.cache.set(key, "response", model="model", ttl=60)
        assert self.cache.get(key) == "response"
        count = self.cache.clear()
        assert count >= 1
        assert self.cache.get(key) is None

    def test_stats(self):
        key = self.cache.hash_prompt("hello", "model", "test")
        self.cache.set(key, "response", model="model", ttl=60)
        self.cache.get(key)  # hit
        self.cache.get("nonexistent")  # miss

        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] >= 1
        assert stats["hit_rate"] > 0
        assert stats["enabled"] is True

    def test_invalid_cache_file(self):
        """Corrupted cache files should be handled gracefully."""
        key = self.cache.hash_prompt("hello", "model", "test")
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text("{invalid json}")
        result = self.cache.get(key)
        assert result is None  # graceful fallback
