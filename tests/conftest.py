"""Shared fixtures and configuration for JobFinder tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_cv_data() -> dict[str, Any]:
    """Sample parsed CV data for testing."""
    return {
        "raw_text": "Experienced software engineer with Python, React, and Docker skills.",
        "sections": {
            "summary": "Software engineer with 5 years of experience.",
            "experience": "Led team of 3 engineers. Built microservices with Python.",
            "education": "BS in Computer Science",
            "skills": "Python, React, Docker, Kubernetes, AWS",
        },
        "skills": ["python", "react", "docker", "kubernetes", "aws"],
        "skill_categories": {
            "python": ["programming_languages"],
            "react": ["frameworks_libraries"],
            "docker": ["cloud_devops"],
        },
        "entities": {"organizations": ["Google", "Amazon"], "degrees": ["BS"]},
        "word_count": 50,
    }


@pytest.fixture
def sample_taxonomy() -> dict[str, Any]:
    """Minimal skills taxonomy for testing."""
    return {
        "programming_languages": {
            "python": {"aliases": ["python3"], "related": ["django", "flask"]},
            "javascript": {"aliases": ["js"], "related": ["react", "node"]},
        },
        "frameworks_libraries": {
            "react": {"aliases": [], "related": ["javascript"]},
            "django": {"aliases": [], "related": ["python"]},
        },
    }


@pytest.fixture
def reset_logging():
    """Reset logging state between tests."""
    import src.utils.logging
    src.utils.logging._initialized = False
    yield
    src.utils.logging._initialized = False


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test file operations."""
    d = tmp_path / "ai_job_finder_test"
    d.mkdir(parents=True, exist_ok=True)
    return d
