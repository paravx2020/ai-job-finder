"""Base scraper class that all job site scrapers implement."""

import json
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast


class SelectorLoader:
    """Loads CSS selectors from config/scraper_selectors.json."""

    _selectors: dict[str, dict[str, str]] | None = None

    @classmethod
    def load(cls, source: str) -> dict[str, str]:
        if cls._selectors is None:
            config_path = (
                Path(__file__).resolve().parent.parent.parent / "config" / "scraper_selectors.json"
            )
            with open(config_path, encoding="utf-8") as f:
                cls._selectors = cast(dict[str, dict[str, str]], json.load(f))
        return cls._selectors.get(source, {})


def with_retry(max_retries: int = 3, backoff_base: float = 2.0):
    """Decorator: retry with exponential backoff on exceptions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = backoff_base**attempt + random.uniform(0, 1)
                        time.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


@dataclass
class JobPosting:
    title: str
    company: str
    description: str
    url: str
    source: str
    salary: str | None = None
    location: str | None = None
    posted_date: datetime | None = None
    raw_data: dict = field(default_factory=dict)


class BaseScraper(ABC):
    def __init__(self, timeout: int = 30000, delay: tuple = (2, 5)):
        self.timeout = timeout
        self.delay = delay

    @property
    def selectors(self) -> dict[str, str]:
        return SelectorLoader.load(self.source_name())

    @abstractmethod
    def search(self, query: str, location: str = "", max_results: int = 25) -> list[JobPosting]:
        """Search for jobs matching the query."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this source (e.g., 'linkedin')."""
        ...
