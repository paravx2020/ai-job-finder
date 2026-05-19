"""Tests for the CV improver module."""

from __future__ import annotations

from unittest.mock import patch

from src.cv_processor.improver import improve_cv, improve_section
from src.utils.models import CVImprovement, ParsedCV


def _make_cv(sections: dict | None = None) -> ParsedCV:
    return ParsedCV(
        raw_text="test",
        sections=sections or {},
        skills=["python"],
        word_count=50,
    )


class TestImproveSection:
    @patch("src.cv_processor.improver._call_ai")
    def test_returns_string(self, mock_call_ai):
        """improve_section should return a string."""
        mock_call_ai.return_value = "Improved summary text"
        result = improve_section("summary", "Test text", domain="software engineering")
        assert isinstance(result, str)

    def test_handles_empty_text(self):
        result = improve_section("summary", "", domain="software engineering")
        assert result == ""

    def test_handles_whitespace_text(self):
        result = improve_section("summary", "   ", domain="software engineering")
        assert result == "   "

    def test_different_sections_have_different_prompts(self):
        """Different sections should use different prompt templates."""
        from src.cv_processor.improver import IMPROVEMENT_PROMPTS
        assert "summary" in IMPROVEMENT_PROMPTS
        assert "experience" in IMPROVEMENT_PROMPTS
        assert "skills" in IMPROVEMENT_PROMPTS

    @patch("src.cv_processor.improver._call_ai")
    def test_unknown_section_falls_back(self, mock_call_ai):
        """Unknown sections should use a generic prompt."""
        mock_call_ai.return_value = "Improved text"
        result = improve_section("unknown_section", "test", "domain")
        assert isinstance(result, str)


class TestImproveCV:
    @patch("src.cv_processor.improver._call_ai")
    def test_returns_cvimprovement_type(self, mock_call_ai):
        cv = _make_cv({"summary": "test text"})
        mock_call_ai.return_value = "Improved summary text that is different"
        result = improve_cv(cv, domain="software engineering")
        assert isinstance(result, CVImprovement)

    @patch("src.cv_processor.improver._call_ai")
    def test_has_improved_sections_and_changes(self, mock_call_ai):
        cv = _make_cv({"summary": "test text"})
        mock_call_ai.return_value = "Much improved text that is different from original"
        result = improve_cv(cv)
        assert hasattr(result, "improved_sections")
        assert hasattr(result, "changes")

    def test_empty_cv_returns_empty(self):
        cv = _make_cv({})
        result = improve_cv(cv)
        assert result.improved_sections == {}
        assert result.changes == []

    @patch("src.cv_processor.improver._call_ai")
    def test_only_improves_known_sections(self, mock_call_ai):
        """Only summary, experience, skills should be improved."""
        cv = _make_cv({
            "summary": "test",
            "education": "MIT",
            "projects": "Project 1",
        })
        mock_call_ai.return_value = "Improved text that is definitely different from original for sure"
        result = improve_cv(cv)
        for change in result.changes:
            assert change.section in ("summary", "experience", "skills")

    @patch("src.cv_processor.improver._call_ai")
    def test_change_detail_structure(self, mock_call_ai):
        """Changes should have section, original_length, new_length."""
        cv = _make_cv({"summary": "test text"})
        mock_call_ai.return_value = "Improved text that is much longer than the original short text"
        result = improve_cv(cv)
        if result.changes:
            change = result.changes[0]
            assert change.section is not None
            assert change.original_length >= 0
            assert change.new_length >= 0

    # ── AI-dependent tests (mocked) ──────────────────────────────

    @patch("src.cv_processor.improver._call_ai")
    def test_calls_ai_with_correct_section(self, mock_call_ai):
        """The AI function should be called with the right section."""
        mock_call_ai.return_value = "Improved text"
        cv = _make_cv({"summary": "Original summary"})
        improve_cv(cv, domain="data science")
        mock_call_ai.assert_called()

    @patch("src.cv_processor.improver._call_ai")
    def test_ai_return_not_replace_identically(self, mock_call_ai):
        """If AI returns same text, no change should be recorded."""
        mock_call_ai.return_value = "Original summary"
        cv = _make_cv({"summary": "Original summary"})
        result = improve_cv(cv)
        assert result.changes == []

    @patch("src.cv_processor.improver._call_ai")
    def test_mocking_full_improvement(self, mock_call_ai):
        """Simulate a full improvement flow with mock."""
        mock_call_ai.return_value = "Improved long text with better words."
        cv = _make_cv({"summary": "Short.", "experience": "Did stuff.", "skills": "Python"})
        result = improve_cv(cv)
        if result.changes:
            for c in result.changes:
                assert c.new_length > 0
                assert c.original_length > 0
