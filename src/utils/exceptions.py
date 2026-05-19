"""Custom exception hierarchy for JobFinder.

All application-specific exceptions inherit from JobFinderError,
enabling unified error handling and structured error reporting.
"""

from __future__ import annotations

from typing import Any


class JobFinderError(Exception):
    """Base exception for all JobFinder errors."""

    error_code: str = "JF-000"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"({detail_str})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, details={self.details!r})"


# ── CV Processing Errors ────────────────────────────────────────────────────


class CVParseError(JobFinderError):
    """Raised when CV file cannot be parsed."""

    error_code = "CV-001"


class CVFormatError(JobFinderError):
    """Raised when CV file format is unsupported or corrupted."""

    error_code = "CV-002"


class CVScoreError(JobFinderError):
    """Raised when CV scoring fails."""

    error_code = "CV-003"


# ── AI Service Errors ───────────────────────────────────────────────────────


class AIServiceError(JobFinderError):
    """Raised when AI API call fails."""

    error_code = "AI-001"


class AITimeoutError(AIServiceError):
    """Raised when AI API call times out."""

    error_code = "AI-002"


class AIQuotaError(AIServiceError):
    """Raised when AI API quota is exceeded."""

    error_code = "AI-003"


# ── Scraping Errors ─────────────────────────────────────────────────────────


class ScraperError(JobFinderError):
    """Raised when web scraper fails."""

    error_code = "SC-001"


class ScraperTimeoutError(ScraperError):
    """Raised when scraper times out waiting for page."""

    error_code = "SC-002"


class ScraperBlockedError(ScraperError):
    """Raised when scraper is blocked (anti-bot, CAPTCHA, etc.)."""

    error_code = "SC-003"


class CaptchaDetectedError(ScraperError):
    """Raised when a CAPTCHA challenge is detected."""

    error_code = "SC-004"


# ── Matching Errors ─────────────────────────────────────────────────────────


class MatchError(JobFinderError):
    """Raised when job matching fails."""

    error_code = "MT-001"


class EmbeddingError(MatchError):
    """Raised when embedding generation fails."""

    error_code = "MT-002"


# ── Application Errors ──────────────────────────────────────────────────────


class ApplyError(JobFinderError):
    """Raised when auto-application fails."""

    error_code = "AP-001"


class FormFillError(ApplyError):
    """Raised when form field cannot be filled."""

    error_code = "AP-002"


class ApplyCancelledError(ApplyError):
    """Raised when user cancels application submission."""

    error_code = "AP-003"


# ── Database Errors ─────────────────────────────────────────────────────────


class DatabaseError(JobFinderError):
    """Raised when database operation fails."""

    error_code = "DB-001"


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    error_code = "DB-002"


# ── Configuration Errors ────────────────────────────────────────────────────


class ConfigError(JobFinderError):
    """Raised when configuration is invalid or missing."""

    error_code = "CF-001"


class MissingAPIKeyError(ConfigError):
    """Raised when a required API key is not configured."""

    error_code = "CF-002"


# ── Validation Errors ───────────────────────────────────────────────────────


class ValidationError(JobFinderError):
    """Raised when input validation fails."""

    error_code = "VL-001"


class FileNotFoundValidationError(ValidationError):
    """Raised when a required file does not exist."""

    error_code = "VL-002"
