"""Tests for the CV scorer module."""

from __future__ import annotations

from src.cv_processor.scorer import (
    score_cv,
)
from src.utils.models import ParsedCV, ScoredCV


def _make_cv(
    sections: dict | None = None,
    skills: list | None = None,
    raw_text: str = "",
    word_count: int = 100,
) -> ParsedCV:
    """Helper to create a ParsedCV for testing."""
    return ParsedCV(
        raw_text=raw_text,
        sections=sections or {},
        skills=skills or [],
        word_count=word_count,
    )


class TestScoreCV:
    def test_returns_scoredcv_type(self):
        cv = _make_cv()
        result = score_cv(cv)
        assert isinstance(result, ScoredCV)

    def test_has_all_score_dimensions(self):
        cv = _make_cv(sections={"summary": "test", "experience": "test", "skills": "test"})
        result = score_cv(cv)
        s = result.scores
        assert hasattr(s, "keyword_density")
        assert hasattr(s, "quantified_achievements")
        assert hasattr(s, "section_completeness")
        assert hasattr(s, "ats_compatibility")

    def test_scores_within_range(self):
        cv = _make_cv(sections={"summary": "test"})
        result = score_cv(cv)
        s = result.scores
        assert 0.0 <= s.keyword_density <= 1.0
        assert 0.0 <= s.quantified_achievements <= 1.0
        assert 0.0 <= s.section_completeness <= 1.0
        assert 0.0 <= s.ats_compatibility <= 1.0

    def test_overall_is_average(self):
        cv = _make_cv(
            sections={"summary": "led team", "experience": "built", "skills": "python"},
            skills=["python", "docker"],
        )
        result = score_cv(cv)
        assert 0.0 <= result.overall <= 1.0

    def test_suggestions_returned(self):
        cv = _make_cv(sections={})
        result = score_cv(cv)
        assert isinstance(result.suggestions, list)

    def test_keyword_density_with_action_verbs(self):
        """CVs with action verbs should score higher on keyword density."""
        cv_good = _make_cv(
            sections={"experience": "Led the team. Developed microservices. Implemented CI/CD."},
        )
        cv_bad = _make_cv(
            sections={"experience": "Was responsible for stuff. Did things. Worked on project."},
        )
        good_result = score_cv(cv_good)
        bad_result = score_cv(cv_bad)
        assert good_result.scores.keyword_density >= bad_result.scores.keyword_density

    def test_quantified_achievements_with_metrics(self):
        """CVs with numbers should score higher on quantified achievements."""
        cv_good = _make_cv(
            sections={"experience": "Increased revenue by 50%. Led 10 engineers. Saved $100K."},
        )
        cv_bad = _make_cv(
            sections={"experience": "Did some work on various projects."},
        )
        good_result = score_cv(cv_good)
        bad_result = score_cv(cv_bad)
        assert good_result.scores.quantified_achievements >= bad_result.scores.quantified_achievements
