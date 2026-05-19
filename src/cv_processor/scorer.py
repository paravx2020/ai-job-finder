"""Score CV quality across multiple dimensions."""

import re

from src.utils.models import ParsedCV, ScoredCV, ScoreDetail

ACTION_VERBS = {
    "achieved", "developed", "implemented", "designed", "led", "managed",
    "created", "built", "launched", "optimized", "delivered", "drove",
    "established", "generated", "improved", "increased", "reduced",
    "resolved", "spearheaded", "transformed", "mentored", "coordinated",
}

QUANTIFIED_PATTERN = re.compile(r"\d+%|\$\d+|\d+x|\d+\s*(?:users|clients|customers|people|team)")


def score_keyword_density(text: str) -> float:
    """Score 0-1 based on presence of relevant keywords."""
    words = len(text.split())
    if words == 0:
        return 0.0
    # Count action verbs and common keywords
    lower_words = set(w.lower() for w in text.split())
    verb_hits = ACTION_VERBS & lower_words
    return min(len(verb_hits) / 5, 1.0)


def score_quantified_achievements(text: str) -> float:
    """Score 0-1 based on quantified results."""
    matches = QUANTIFIED_PATTERN.findall(text)
    return min(len(matches) / 3, 1.0)


def score_section_completeness(data: ParsedCV) -> float:
    """Score 0-1 based on which sections are present."""
    sections = data.sections
    required = {"summary", "experience", "education", "skills"}
    bonus = {"projects", "certifications"}
    present = sum(1 for s in required if sections.get(s))
    extras = sum(1 for s in bonus if sections.get(s))
    return min((present + extras * 0.5) / len(required), 1.0)


def score_ats_compatibility(text: str) -> float:
    """Score 0-1 based on ATS-friendly formatting."""
    score = 1.0
    # Penalize tables
    if re.search(r"\|.*\|.*\|", text):
        score -= 0.15
    # Penalize long unbroken paragraphs
    for para in text.split("\n"):
        if len(para.split()) > 100:
            score -= 0.05
    # Penalize missing contact info patterns
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        score -= 0.2
    if not re.search(r"\+\d[\d\s\-()]{7,}", text):
        score -= 0.1
    return max(score, 0.0)


def score_cv(data: ParsedCV) -> ScoredCV:
    text = data.raw_text
    sections = data.sections
    full_text = "\n".join(sections.values())

    detail = ScoreDetail(
        keyword_density=round(score_keyword_density(full_text), 2),
        quantified_achievements=round(score_quantified_achievements(full_text), 2),
        section_completeness=round(score_section_completeness(data), 2),
        ats_compatibility=round(score_ats_compatibility(text), 2),
    )
    overall = round(
        (detail.keyword_density + detail.quantified_achievements + detail.section_completeness + detail.ats_compatibility) / 4,
        2,
    )

    suggestions = []
    if detail.keyword_density < 0.5:
        suggestions.append("Add more action verbs (e.g., 'achieved', 'implemented', 'optimized').")
    if detail.quantified_achievements < 0.5:
        suggestions.append("Include quantified results (e.g., 'increased revenue by 20%').")
    if detail.section_completeness < 0.8:
        suggestions.append("Add missing sections (projects, certifications).")
    if detail.ats_compatibility < 0.7:
        suggestions.append("Simplify formatting for ATS parsers (avoid tables, add contact info).")

    return ScoredCV(scores=detail, overall=overall, suggestions=suggestions)
