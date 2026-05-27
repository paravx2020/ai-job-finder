"""Parse CV files (PDF, DOCX) into structured data."""

import re
from pathlib import Path

import docx
import PyPDF2

from src.utils.models import ParsedCV
from src.utils.skills import categorize_skill, get_all_skills

# Lazy spaCy load — torch dependency may not be available
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy as _spacy_mod

        _nlp = _spacy_mod.load("en_core_web_sm")
    except Exception:
        _nlp = False  # sentinel: already tried
    return _nlp if _nlp else None


def _get_skill_set() -> set[str]:
    """Get all known skills from the taxonomy (including aliases)."""
    return get_all_skills()


def extract_text_from_pdf(path: Path) -> str:
    text = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text)


def extract_text_from_docx(path: Path) -> str:
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext == ".docx":
        return extract_text_from_docx(path)
    elif ext == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _find_section(text: str, heading: str, next_headings: list[str]) -> str:
    """Extract text under a given section heading.

    Matches heading lines flexibly — the heading keyword can appear anywhere
    on the line (e.g. ``summary`` matches ``PROFESSIONAL SUMMARY`` or
    ``Summary of Qualifications``).
    """
    # Flexible pattern: any non-empty line containing the heading keyword as a word,
    # optionally with trailing colon/spaces before the line break
    heading_pattern = rf"\s*[^\n]*\b{re.escape(heading)}s?\b[^\n]*:?\s*\n"

    # Build same flexible pattern for each successor heading
    next_patterns = [rf"\s*[^\n]*\b{re.escape(h)}s?\b[^\n]*:?\s*\n" for h in next_headings]
    next_combined = "|".join(next_patterns)

    if next_headings:
        pattern = re.compile(
            rf"(?:^|\n){heading_pattern}(.*?)(?=\n(?:{next_combined})|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
    else:
        pattern = re.compile(
            rf"(?:^|\n){heading_pattern}(.*?)(?=\Z)",
            re.IGNORECASE | re.DOTALL,
        )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_skills(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Extract skills from text using the skills taxonomy with word-boundary matching.

    Returns:
        Tuple of (list of detected skills, dict mapping skill to categories)
    """
    known_skills = _get_skill_set()
    found_skills = []
    skill_categories = {}

    # Sort longest first so multi-word skills are matched before their sub-words
    for skill in sorted(known_skills, key=len, reverse=True):
        # Match skill as a whole word — (?<!\w)/(?!\w) assertions are
        # content-aware and handle punctuation/symbols in skill names
        # (unlike \b which chokes on non-\w chars like + / . #).
        pattern = re.compile(rf"(?<!\w){re.escape(skill)}(?!\w)", re.IGNORECASE)
        if pattern.search(text):
            found_skills.append(skill)
            categories = categorize_skill(skill)
            if categories:
                skill_categories[skill] = categories

    return found_skills, skill_categories


def extract_entities(text: str) -> dict:
    """Extract named entities using spaCy."""
    nlp = _get_nlp()
    if nlp is None:
        return {"organizations": [], "degrees": []}
    doc = nlp(text[:50000])  # limit to avoid OOM
    orgs = list(set(ent.text for ent in doc.ents if ent.label_ == "ORG"))
    degrees = list(set(ent.text for ent in doc.ents if ent.label_ == "DEGREE"))
    return {"organizations": orgs, "degrees": degrees}


def parse_cv(path: Path) -> ParsedCV:
    text = extract_text(path)
    headings = [
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "publications",
        "languages",
        "interests",
    ]

    sections = {}
    for i, h in enumerate(headings):
        remaining = headings[i + 1 :] if i + 1 < len(headings) else []
        content = _find_section(text, h, remaining)
        if content:
            sections[h] = content

    # If sections not found by heading, use heuristics
    if not sections.get("skills"):
        sections["skills"] = ""

    skills, skill_categories = extract_skills(text)
    entities = extract_entities(text)

    return ParsedCV(
        raw_text=text[:10000],
        sections=sections,
        skills=skills,
        skill_categories=skill_categories,
        entities=entities,
        word_count=len(text.split()),
    )
