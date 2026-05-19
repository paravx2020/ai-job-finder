"""Input validation utilities for JobFinder.

Provides validation functions for common inputs using Pydantic models
and standalone checks.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.utils.exceptions import ValidationError


def validate_cv_path(path: str | Path) -> Path:
    """Validate and resolve a CV file path.

    Args:
        path: Path to a PDF or DOCX file.

    Returns:
        Resolved Path object.

    Raises:
        ValidationError: If the path is invalid or file doesn't exist.
    """
    try:
        p = Path(path)
    except TypeError:
        raise ValidationError("Invalid CV path type", details={"path": str(path)})

    if not p.exists():
        raise ValidationError("CV file not found", details={"path": str(p)})

    if not p.is_file():
        raise ValidationError("CV path is not a file", details={"path": str(p)})

    ext = p.suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise ValidationError(
            "Unsupported CV format",
            details={"path": str(p), "extension": ext, "supported": ".pdf, .docx"},
        )

    return p.resolve()


def validate_email(email: str) -> bool:
    """Validate an email address format.

    Args:
        email: The email address to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate a URL format.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL has a valid format.
    """
    if not url or not isinstance(url, str):
        return False
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def validate_salary_range(salary: str | None) -> bool:
    """Validate a salary string format.

    Accepts formats like: "$50,000", "$50k", "$50K-$100K", "$50,000 - $100,000".

    Args:
        salary: The salary string to validate.

    Returns:
        True if valid format or None.
    """
    if salary is None:
        return True
    if not isinstance(salary, str):
        return False
    pattern = r"^[\$€£]?\s*[\d,]+(k|K)?(\s*[-–to]+\s*[\$€£]?\s*[\d,]+(k|K)?)?$"
    return bool(re.match(pattern, salary.strip()))


def validate_page_number(page: int, total: int) -> int:
    """Validate and normalize a 1-based page number.

    Args:
        page: Requested page number (1-based).
        total: Total number of pages available.

    Returns:
        Validated page number.

    Raises:
        ValidationError: If the page number is out of range.
    """
    if page < 1:
        raise ValidationError("Page number must be >= 1", details={"page": page})
    if page > total:
        raise ValidationError(
            "Page number exceeds total pages",
            details={"page": page, "total": total},
        )
    return page
