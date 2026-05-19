"""Pydantic v2 models for JobFinder data types.

Provides typed, validated data structures for CV parsing, scoring,
improvement, job matching, and search results.

Usage:
    from src.utils.models import ParsedCV, ScoredCV, MatchResult

    parsed = ParsedCV(**parse_cv_result)
    parsed.sections.keys()  # typed access, not dict["sections"]
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# ── CV Processor Models ─────────────────────────────────────────────────────

class CVSection(BaseModel):
    """A single section of a parsed CV."""
    name: str
    content: str = ""


class ParsedCV(BaseModel):
    """Structured data extracted from a CV file."""
    raw_text: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    skill_categories: dict[str, list[str]] = Field(default_factory=dict)
    entities: dict[str, list[str]] = Field(default_factory=lambda: {"organizations": [], "degrees": []})
    word_count: int = Field(default=0, ge=0)


class ScoreDetail(BaseModel):
    """Individual scoring dimension."""
    keyword_density: float = Field(default=0.0, ge=0.0, le=1.0)
    quantified_achievements: float = Field(default=0.0, ge=0.0, le=1.0)
    section_completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    ats_compatibility: float = Field(default=0.0, ge=0.0, le=1.0)


class ScoredCV(BaseModel):
    """CV with quality scores."""
    scores: ScoreDetail = Field(default_factory=ScoreDetail)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    suggestions: list[str] = Field(default_factory=list)


class ChangeDetail(BaseModel):
    """Record of an AI improvement change."""
    section: str
    original_length: int = Field(default=0, ge=0)
    new_length: int = Field(default=0, ge=0)


class CVImprovement(BaseModel):
    """AI-powered CV improvement results."""
    improved_sections: dict[str, str] = Field(default_factory=dict)
    changes: list[ChangeDetail] = Field(default_factory=list)


# ── Job & Matching Models ───────────────────────────────────────────────────

class JobData(BaseModel):
    """Structured job posting data."""
    title: str = ""
    company: str = ""
    description: str = ""
    url: str = ""
    source: str = ""
    salary: str | None = None
    location: str | None = None
    posted_date: str | None = None


class MatchResult(BaseModel):
    """A job matching result with score."""
    job: dict[str, Any] = Field(default_factory=dict)
    match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_percentage: str = ""
    reason: str = ""


# ── CLI Output Models ──────────────────────────────────────────────────────

class AnalyzeResult(BaseModel):
    """Complete result of the analyze command."""
    parsed: ParsedCV = Field(default_factory=ParsedCV)
    score: ScoredCV = Field(default_factory=ScoredCV)
    improvements: CVImprovement = Field(default_factory=CVImprovement)


class SearchResult(BaseModel):
    """Complete result of the search command."""
    query: str = ""
    location: str = ""
    total_matches: int = 0
    matches: list[MatchResult] = Field(default_factory=list)
