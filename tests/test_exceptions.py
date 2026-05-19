"""Tests for the custom exception hierarchy."""

from __future__ import annotations

from src.utils.exceptions import (
    ApplyCancelledError,
    ApplyError,
    CaptchaDetectedError,
    ConfigError,
    CVParseError,
    DatabaseConnectionError,
    DatabaseError,
    FormFillError,
    JobFinderError,
    MissingAPIKeyError,
    ScraperBlockedError,
    ScraperError,
    ScraperTimeoutError,
)


class TestJobFinderError:
    """Tests for the base exception class."""

    def test_error_code(self) -> None:
        """Each exception should have a unique error code following XXX-NNN pattern."""
        import re

        def _collect_all(exc_cls: type[JobFinderError]) -> list[type[JobFinderError]]:
            result: list[type[JobFinderError]] = []
            for sub in exc_cls.__subclasses__():
                result.append(sub)
                result.extend(_collect_all(sub))
            return result

        codes: dict[str, type[JobFinderError]] = {}
        for sub in _collect_all(JobFinderError):
            code = sub.error_code
            # Check pattern: prefix-ddd (e.g., CV-001, AI-002, SC-003)
            assert re.match(r'^[A-Z]{2,3}-\d{3}$', code), \
                f"Invalid error code format: {code} in {sub.__name__}"
            assert code not in codes, f"Duplicate error code: {code}"
            codes[code] = sub

        # All expected error codes present
        expected = {"CV-001", "CV-002", "CV-003",
                    "AI-001", "AI-002", "AI-003",
                    "SC-001", "SC-002", "SC-003", "SC-004",
                    "MT-001", "MT-002",
                    "AP-001", "AP-002", "AP-003",
                    "DB-001", "DB-002",
                    "CF-001", "CF-002",
                    "VL-001", "VL-002"}
        for code in expected:
            assert code in codes, f"Missing error code: {code}"

    def test_str_representation(self):
        """__str__ should include error code and message."""
        e = CVParseError("Failed to parse", details={"file": "cv.pdf"})
        s = str(e)
        assert "[CV-001]" in s
        assert "Failed to parse" in s

    def test_repr_representation(self):
        """__repr__ should show class name and args."""
        e = ScraperError("Timeout")
        r = repr(e)
        assert "ScraperError" in r
        assert "Timeout" in r

    def test_isinstance_base(self):
        """All exceptions should be instanceof JobFinderError."""
        assert isinstance(CVParseError(""), JobFinderError)
        assert isinstance(ScraperError(""), JobFinderError)
        assert isinstance(ApplyError(""), JobFinderError)
        assert isinstance(ConfigError(""), JobFinderError)
        assert isinstance(DatabaseError(""), JobFinderError)

    def test_inheritance_chain(self):
        """Subclass exceptions should inherit from their parent."""
        assert issubclass(CaptchaDetectedError, ScraperError)
        assert issubclass(ScraperTimeoutError, ScraperError)
        assert issubclass(ScraperBlockedError, ScraperError)
        assert issubclass(MissingAPIKeyError, ConfigError)
        assert issubclass(DatabaseConnectionError, DatabaseError)
        assert issubclass(FormFillError, ApplyError)
        assert issubclass(ApplyCancelledError, ApplyError)

    def test_details_passed_correctly(self):
        """Details dict should be preserved."""
        details = {"file": "test.pdf", "line": 42}
        e = CVParseError("Parse error", details=details)
        assert e.details == details

    def test_empty_details(self):
        """Exceptions without details should have empty dict."""
        e = ScraperError("Simple error")
        assert e.details == {}
