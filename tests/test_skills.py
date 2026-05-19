"""Tests for skills taxonomy utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils.skills import (
    _build_fallback_taxonomy,
    categorize_skill,
    expand_skills,
    find_related_skills,
    get_all_skills,
    get_skill_count,
    load_taxonomy,
)


class TestLoadTaxonomy:
    def test_loads_from_default_path(self):
        """load_taxonomy should load from data/skills_taxonomy.json by default."""
        taxonomy = load_taxonomy()
        assert len(taxonomy) >= 7  # at least 7 categories
        assert "programming_languages" in taxonomy
        assert "python" in taxonomy["programming_languages"]

    def test_fallback_on_missing_file(self, tmp_path):
        """load_taxonomy should fall back gracefully on missing file."""
        taxonomy = load_taxonomy(path=tmp_path / "nonexistent.json")
        assert len(taxonomy) >= 1  # fallback has skills

    def test_fallback_on_invalid_json(self, tmp_path):
        """load_taxonomy should fall back on invalid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json}")
        taxonomy = load_taxonomy(path=bad_file)
        assert len(taxonomy) >= 1

    def test_structure(self):
        """Each skill should have aliases and related fields."""
        taxonomy = load_taxonomy()
        for category, skills in taxonomy.items():
            for name, data in skills.items():
                assert "aliases" in data
                assert "related" in data


class TestCategorizeSkill:
    def test_programming_language(self):
        cats = categorize_skill("python")
        assert "programming_languages" in cats

    def test_framework(self):
        cats = categorize_skill("react")
        assert "frameworks_libraries" in cats

    def test_alias_resolution(self):
        cats = categorize_skill("python3")
        assert "programming_languages" in cats

    def test_case_insensitive(self):
        cats = categorize_skill("Python")
        assert "programming_languages" in cats

    def test_unknown_skill(self):
        cats = categorize_skill("madeupskill123")
        assert cats == []


class TestFindRelated:
    def test_returns_list(self):
        related = find_related_skills("python")
        assert isinstance(related, list)
        assert len(related) > 0

    def test_unknown_skill(self):
        related = find_related_skills("madeup")
        assert related == []


class TestGetAllSkills:
    def test_returns_set(self):
        skills = get_all_skills()
        assert isinstance(skills, set)
        assert len(skills) > 100  # taxonomy has 100+ including aliases

    def test_includes_aliases(self):
        skills = get_all_skills()
        assert "python3" in skills or "js" in skills  # known aliases


class TestExpandSkills:
    def test_expands_to_set(self):
        expanded = expand_skills(["python"])
        assert isinstance(expanded, set)
        assert "python" in expanded

    def test_includes_related(self):
        expanded = expand_skills(["python"])
        assert "django" in expanded or "flask" in expanded

    def test_multiple_skills(self):
        expanded = expand_skills(["python", "react"])
        assert "python" in expanded
        assert "react" in expanded


class TestGetSkillCount:
    def test_returns_dict(self):
        counts = get_skill_count()
        assert isinstance(counts, dict)
        total = sum(counts.values())
        assert total >= 100  # at least 100 skills
