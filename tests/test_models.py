"""Tests for Pydantic validation models."""

from __future__ import annotations

from src.utils.models import (
    ChangeDetail,
    CVImprovement,
    CVSection,
    MatchResult,
    ParsedCV,
    ScoreDetail,
    ScoredCV,
)


class TestParsedCV:
    def test_default_construction(self):
        """ParsedCV should have sensible defaults."""
        cv = ParsedCV()
        assert cv.raw_text == ""
        assert cv.sections == {}
        assert cv.skills == []
        assert cv.word_count == 0

    def test_full_construction(self):
        """ParsedCV should accept all fields."""
        cv = ParsedCV(
            raw_text="test text",
            sections={"summary": "test"},
            skills=["python"],
            skill_categories={"python": ["programming_languages"]},
            entities={"organizations": ["Google"], "degrees": ["BS"]},
            word_count=100,
        )
        assert cv.raw_text == "test text"
        assert cv.sections["summary"] == "test"
        assert cv.skills == ["python"]
        assert cv.word_count == 100

    def test_word_count_non_negative(self):
        """word_count should be >= 0."""
        cv = ParsedCV(word_count=0)
        assert cv.word_count == 0

    def test_serialization(self):
        """ParsedCV should serialize to dict via model_dump."""
        cv = ParsedCV(word_count=10, skills=["a"])
        d = cv.model_dump()
        assert d["word_count"] == 10
        assert d["skills"] == ["a"]


class TestScoreDetail:
    def test_default_scores(self):
        """ScoreDetail should default to 0.0."""
        s = ScoreDetail()
        assert s.keyword_density == 0.0
        assert s.quantified_achievements == 0.0
        assert s.section_completeness == 0.0
        assert s.ats_compatibility == 0.0

    def test_score_range(self):
        """Scores should be between 0 and 1."""
        s = ScoreDetail(keyword_density=0.5, quantified_achievements=1.0,
                        section_completeness=0.75, ats_compatibility=0.0)
        assert 0 <= s.keyword_density <= 1
        assert 0 <= s.quantified_achievements <= 1
        assert 0 <= s.section_completeness <= 1
        assert 0 <= s.ats_compatibility <= 1


class TestScoredCV:
    def test_default_construction(self):
        """ScoredCV should have defaults."""
        sc = ScoredCV()
        assert sc.overall == 0.0
        assert sc.suggestions == []

    def test_full_construction(self):
        """ScoredCV should accept all fields."""
        sc = ScoredCV(
            scores=ScoreDetail(keyword_density=0.8, quantified_achievements=0.6,
                               section_completeness=0.9, ats_compatibility=0.7),
            overall=0.75,
            suggestions=["Add more metrics", "Fix formatting"],
        )
        assert sc.scores.keyword_density == 0.8
        assert sc.overall == 0.75
        assert len(sc.suggestions) == 2


class TestCVImprovement:
    def test_defaults(self):
        imp = CVImprovement()
        assert imp.improved_sections == {}
        assert imp.changes == []

    def test_with_changes(self):
        imp = CVImprovement(
            improved_sections={"summary": "New text"},
            changes=[ChangeDetail(section="summary", original_length=10, new_length=20)],
        )
        assert "summary" in imp.improved_sections
        assert imp.changes[0].original_length == 10


class TestMatchResult:
    def test_defaults(self):
        m = MatchResult()
        assert m.match_score == 0.0
        assert m.match_percentage == ""

    def test_full(self):
        m = MatchResult(
            job={"title": "Engineer"},
            match_score=0.85,
            match_percentage="85%",
            reason="Good skill match",
        )
        assert m.match_score == 0.85
        assert m.reason == "Good skill match"
