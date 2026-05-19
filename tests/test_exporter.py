"""Tests for the export module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils.exporter import (
    build_analyze_export,
    build_search_export,
    export_results,
)


class TestBuildExportData:
    def test_build_analyze_export(self):
        """build_analyze_export should structure data correctly."""
        data = build_analyze_export(
            parsed={
                "sections": {"summary": "test", "experience": "test"},
                "skills": ["python"],
                "skill_categories": {"python": ["prog"]},
                "word_count": 100,
            },
            score_data={
                "scores": {"keyword_density": 0.8},
                "overall": 0.75,
                "suggestions": ["Add metrics"],
            },
            improvement={
                "improved_sections": {"summary": "new"},
                "changes": [{"section": "summary", "original_length": 10, "new_length": 20}],
            },
        )
        assert "parsed" in data
        assert "score" in data
        assert "improvements" in data
        assert data["parsed"]["word_count"] == 100

    def test_build_search_export(self):
        """build_search_export should structure data correctly."""
        data = build_search_export(
            matches=[
                {
                    "job": {"title": "Dev", "company": "Acme", "url": "http://x",
                            "source": "linkedin", "location": "NYC"},
                    "match_score": 0.85,
                    "match_percentage": "85%",
                    "reason": "Good match",
                }
            ],
            query="developer",
            location="NYC",
        )
        assert data["search_metadata"]["query"] == "developer"
        assert len(data["matches"]) == 1
        assert data["matches"][0]["job"]["title"] == "Dev"


class TestExportResults:
    def test_export_json(self, temp_dir: Path):
        """export_results should write valid JSON."""
        out = temp_dir / "report.json"
        path = export_results({"key": "value"}, str(out))
        assert Path(path).exists()

        with open(path) as f:
            data = json.load(f)
        assert "export_metadata" in data
        assert data["key"] == "value"

    def test_export_invalid_extension(self, temp_dir: Path):
        """Unsupported extensions should raise ValueError."""
        out = temp_dir / "report.txt"
        with pytest.raises(ValueError, match="Unsupported"):
            export_results({}, str(out))
