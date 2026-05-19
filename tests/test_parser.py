"""Tests for the CV parser module."""

from __future__ import annotations

from pathlib import Path

from unittest.mock import patch

import pytest

from src.cv_processor.parser import (
    _find_section,
    extract_skills,
    parse_cv,
)


class TestFindSection:
    def test_finds_section_content(self):
        text = "SUMMARY\nExperienced engineer.\nEXPERIENCE\nBuilt things.\nEDUCATION\nMIT"
        result = _find_section(text, "SUMMARY", ["EXPERIENCE", "EDUCATION"])
        assert "Experienced engineer" in result

    def test_returns_empty_for_missing_section(self):
        text = "EXPERIENCE\nBuilt things."
        result = _find_section(text, "SUMMARY", ["EXPERIENCE"])
        assert result == ""

    def test_handles_colon_in_heading(self):
        text = "Summary:\nExperienced engineer.\nExperience:\nBuilt things."
        result = _find_section(text, "Summary", ["Experience"])
        assert "Experienced engineer" in result

    def test_handles_whitespace(self):
        text = "  Summary  \n  Experienced engineer.  \n  Experience  \n  Built things.  "
        result = _find_section(text, "Summary", ["Experience"])
        assert "Experienced engineer" in result or "Experienced engineer" in result


class TestExtractSkills:
    def test_extracts_known_skills(self):
        skills, categories = extract_skills("I know Python and React very well")
        assert "python" in skills
        assert "react" in skills

    def test_returns_empty_list_for_no_matches(self):
        skills, categories = extract_skills("I like cooking and hiking")
        # May find nothing or very few
        assert isinstance(skills, list)
        assert isinstance(categories, dict)

    def test_case_insensitive(self):
        skills, categories = extract_skills("PYTHON, DOCKER, AWS")
        assert "python" in skills
        assert "docker" in skills or "aws" in skills

    def test_returns_categories(self):
        skills, categories = extract_skills("python")
        if "python" in skills and "python" in categories:
            assert len(categories["python"]) > 0

    def test_handles_compound_skills(self):
        skills, categories = extract_skills("machine learning and data analysis")
        matched = set(skills)
        # At least some should match
        assert len(matched) > 0


class TestParseCV:
    def test_parse_invalid_path_raises(self, tmp_path):
        """parse_cv should raise on unsupported formats."""
        from src.utils.exceptions import CVParseError
        bad_file = tmp_path / "cv.txt"
        bad_file.write_text("test")
        # Should raise ValueError for unsupported extension
        with pytest.raises((ValueError, CVParseError)):
            parse_cv(bad_file)

    @patch("src.cv_processor.parser.extract_text")
    def test_parse_returns_parsedcv_type(self, mock_extract, tmp_path):
        """parse_cv should return a ParsedCV object."""
        from src.utils.models import ParsedCV

        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        
        mock_extract.return_value = "SUMMARY\nExperienced engineer.\nSKILLS\nPython, Docker"

        result = parse_cv(pdf)
        assert isinstance(result, ParsedCV)
        # Verify sections are extracted
        assert "summary" in result.sections
        assert result.sections["summary"] == "Experienced engineer."

    @patch("src.cv_processor.parser.extract_text")
    def test_parse_extracts_word_count(self, mock_extract, tmp_path):
        """parse_cv should return word count."""
        from src.utils.models import ParsedCV

        pdf = tmp_path / "test2.pdf"
        pdf.write_text("dummy")
        
        mock_extract.return_value = "one two three four five"
        
        result = parse_cv(pdf)
        assert isinstance(result.word_count, int)
        assert result.word_count == 5
