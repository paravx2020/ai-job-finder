"""Tests for input validation utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.exceptions import ValidationError
from src.utils.validators import validate_cv_path, validate_email, validate_url


class TestValidateEmail:
    def test_valid_emails(self):
        assert validate_email("user@example.com") is True
        assert validate_email("a.b@domain.co") is True
        assert validate_email("user+tag@example.org") is True

    def test_invalid_emails(self):
        assert validate_email("") is False
        assert validate_email("not-an-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email(None) is False
        assert validate_email(123) is False


class TestValidateURL:
    def test_valid_urls(self):
        assert validate_url("https://example.com") is True
        assert validate_url("http://linkedin.com/jobs/123") is True
        assert validate_url("https://www.glassdoor.com/Job/index.htm") is True

    def test_invalid_urls(self):
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url(None) is False
        assert validate_url(123) is False


class TestValidateCVPath:
    def test_missing_file_raises(self):
        with pytest.raises(ValidationError, match="not found"):
            validate_cv_path("/nonexistent/path/cv.pdf")

    def test_wrong_extension_raises(self, tmp_path):
        f = tmp_path / "cv.txt"
        f.write_text("hello")
        with pytest.raises(ValidationError, match="Unsupported"):
            validate_cv_path(str(f))

    def test_valid_pdf(self, tmp_path):
        f = tmp_path / "cv.pdf"
        f.write_text("%PDF-1.4 fake")
        result = validate_cv_path(str(f))
        assert isinstance(result, Path)
        assert result.name == "cv.pdf"
