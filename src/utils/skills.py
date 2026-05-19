"""Skills taxonomy utilities for JobFinder.

Loads a hierarchical skills taxonomy from JSON and provides
categorization, expansion, and related-skill lookup functions.

Usage:
    from src.utils.skills import load_taxonomy, categorize_skill, expand_skills

    taxonomy = load_taxonomy()
    categories = categorize_skill("python")  # ["programming_languages"]
    expanded = expand_skills(["python"])     # {"python", "django", "flask", ...}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Default minimal skill set if taxonomy file is missing
_FALLBACK_SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c", "go", "rust",
    "ruby", "php", "sql", "html", "css", "react", "angular", "vue",
    "node.js", "django", "flask", "spring", "rails", "docker",
    "kubernetes", "aws", "git", "linux", "agile", "scrum",
    "machine learning", "data analysis", "tensorflow", "pytorch",
    "pandas", "numpy", "postgresql", "mysql", "mongodb", "redis",
}


def load_taxonomy(path: str | Path | None = None) -> dict[str, Any]:
    """Load the skills taxonomy from JSON file.

    Args:
        path: Path to the taxonomy JSON file. Defaults to data/skills_taxonomy.json.

    Returns:
        Dictionary mapping category names to skill definitions.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_taxonomy.json"

    try:
        with open(path, encoding="utf-8") as f:
            taxonomy = json.load(f)
        logger.info("Loaded skills taxonomy from %s", path)
        return taxonomy
    except FileNotFoundError:
        logger.warning("Skills taxonomy not found at %s, using fallback set", path)
        return _build_fallback_taxonomy()
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in skills taxonomy: %s", e)
        return _build_fallback_taxonomy()


def _build_fallback_taxonomy() -> dict[str, Any]:
    """Build a minimal taxonomy from the fallback skill set."""
    return {
        "programming_languages": {skill: {"aliases": [], "related": []} for skill in _FALLBACK_SKILLS},
    }


def get_all_skills(taxonomy: dict[str, Any] | None = None) -> set[str]:
    """Get a flat set of all skill names (including aliases).

    Args:
        taxonomy: Pre-loaded taxonomy dict. Loads from file if None.

    Returns:
        Set of all skill names and their aliases (lowercase).
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    skills: set[str] = set()
    for category in taxonomy.values():
        for skill_name, skill_data in category.items():
            skills.add(skill_name.lower())
            for alias in skill_data.get("aliases", []):
                skills.add(alias.lower())
    return skills


def categorize_skill(skill: str, taxonomy: dict[str, Any] | None = None) -> list[str]:
    """Find which categories a skill belongs to.

    Args:
        skill: The skill name to look up (case-insensitive).
        taxonomy: Pre-loaded taxonomy dict. Loads from file if None.

    Returns:
        List of category names the skill belongs to.
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    skill_lower = skill.lower()
    categories = []

    for category_name, skills in taxonomy.items():
        for skill_name, skill_data in skills.items():
            if skill_lower == skill_name.lower():
                categories.append(category_name)
            elif skill_lower in [a.lower() for a in skill_data.get("aliases", [])]:
                categories.append(category_name)

    return categories


def find_related_skills(skill: str, taxonomy: dict[str, Any] | None = None) -> list[str]:
    """Find skills related to the given skill.

    Args:
        skill: The skill name to look up (case-insensitive).
        taxonomy: Pre-loaded taxonomy dict. Loads from file if None.

    Returns:
        List of related skill names.
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    skill_lower = skill.lower()

    for category in taxonomy.values():
        for skill_name, skill_data in category.items():
            if skill_lower == skill_name.lower():
                return skill_data.get("related", [])
            if skill_lower in [a.lower() for a in skill_data.get("aliases", [])]:
                return skill_data.get("related", [])

    return []


def expand_skills(skills: list[str], taxonomy: dict[str, Any] | None = None) -> set[str]:
    """Expand a list of skills to include aliases and related skills.

    Args:
        skills: List of seed skill names.
        taxonomy: Pre-loaded taxonomy dict. Loads from file if None.

    Returns:
        Set of expanded skills (original + aliases + related).
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    expanded: set[str] = set()

    for skill in skills:
        skill_lower = skill.lower()
        expanded.add(skill_lower)

        # Add aliases
        for category in taxonomy.values():
            for skill_name, skill_data in category.items():
                if skill_lower == skill_name.lower():
                    expanded.add(skill_name.lower())
                    for alias in skill_data.get("aliases", []):
                        expanded.add(alias.lower())
                    for related in skill_data.get("related", []):
                        expanded.add(related.lower())
                    break

    return expanded


def get_skill_count(taxonomy: dict[str, Any] | None = None) -> dict[str, int]:
    """Get the count of skills per category.

    Args:
        taxonomy: Pre-loaded taxonomy dict. Loads from file if None.

    Returns:
        Dictionary mapping category names to skill counts.
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    return {category: len(skills) for category, skills in taxonomy.items()}
