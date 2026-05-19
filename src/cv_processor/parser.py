"""Parse CV files (PDF, DOCX) into structured data."""

import re
from pathlib import Path

import docx
import PyPDF2
import spacy

from src.utils.models import ParsedCV
from src.utils.skills import categorize_skill, get_all_skills

# Load spaCy model (download: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


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
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _find_section(text: str, heading: str, next_headings: list[str]) -> str:
    """Extract text under a given section heading."""
    pattern = re.compile(
        rf"(?:^|\n)\s*{re.escape(heading)}s*:?\s*\n(.*?)(?=\n\s*(?:{'|'.join(next_headings)})\s*:?\s*\n|\Z)",
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_skills(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Extract skills from text using the skills taxonomy.

    Returns:
        Tuple of (list of detected skills, dict mapping skill to categories)
    """
    known_skills = _get_skill_set()
    text_lower = text.lower()
    found_skills = []
    skill_categories = {}

    for skill in known_skills:
        if skill in text_lower:
            found_skills.append(skill)
            categories = categorize_skill(skill)
            if categories:
                skill_categories[skill] = categories

    return sorted(found_skills), skill_categories


def extract_entities(text: str) -> dict:
    """Extract named entities using spaCy."""
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
