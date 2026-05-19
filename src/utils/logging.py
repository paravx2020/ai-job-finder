"""Structured logging system for JobFinder.

Provides a centralized logging setup with Rich console integration,
JSON formatting for file output, and context-aware log injection.

Usage:
    from src.utils.logging import get_logger, setup_logging

    setup_logging(verbose=True)  # call once at app startup
    logger = get_logger(__name__)
    logger.info("Starting CV analysis")
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# ── Context Variables for Log Enrichment ─────────────────────────────────────

_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


# ── Custom Formatter ────────────────────────────────────────────────────────

class ContextFormatter(logging.Formatter):
    """Formatter that injects context variables into log records."""

    def format(self, record: logging.LogRecord) -> str:
        # Inject context variables into the record
        context = _log_context.get()
        for key, value in context.items():
            setattr(record, f"ctx_{key}", value)

        # Add module shorthand
        record.module_short = record.module[:15] if record.module else ""

        return super().format(record)


# ── Public API ───────────────────────────────────────────────────────────────

_console = Console(stderr=True)
_initialized = False


def setup_logging(
    verbose: bool = False,
    quiet: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure the root logger for the application.

    Call this once at application startup (in main.py CLI group).

    Args:
        verbose: Enable DEBUG level output.
        quiet: Only show WARNING and above.
        log_file: Optional file path for JSON log output.
    """
    global _initialized
    if _initialized:
        return

    # Determine log level
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure root logger
    root_logger = logging.getLogger("ai_job_finder")
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Rich console handler (for stderr)
    rich_handler = RichHandler(
        console=_console,
        show_time=True,
        show_path=False,
        show_level=True,
        markup=False,
        rich_tracebacks=True,
        tracebacks_show_locals=verbose,
    )
    rich_handler.setLevel(level)
    rich_handler.setFormatter(
        ContextFormatter("%(message)s", datefmt="[%X]")
    )
    root_logger.addHandler(rich_handler)

    # Optional file handler (JSON format)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            ContextFormatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                '"module":"%(module_short)s","function":"%(funcName)s",'
                '"line":%(lineno)d,"message":"%(message)s"}',
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ["playwright", "urllib3", "httpx", "openai", "google"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger scoped to the given module name.

    Automatically prefixes with 'ai_job_finder.' for consistent naming.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        Configured logger instance.
    """
    # Normalize module name to ai_job_finder.*
    if not name.startswith("ai_job_finder"):
        name = name.replace("src.", "ai_job_finder.", 1)
        if not name.startswith("ai_job_finder"):
            name = f"ai_job_finder.{name}"

    return logging.getLogger(name)


# ── Context Manager for Log Enrichment ───────────────────────────────────────

class LogContext:
    """Context manager that adds key-value pairs to all log records
    within its scope.

    Usage:
        with LogContext(user_id="123", action="analyze"):
            logger.info("Processing CV")
            # Output includes: ctx_user_id=123, ctx_action=analyze
    """

    def __init__(self, **kwargs: Any) -> None:
        self._extra = kwargs
        self._token = None

    def __enter__(self) -> LogContext:
        current = _log_context.get()
        merged = {**current, **self._extra}
        self._token = _log_context.set(merged)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _log_context.reset(self._token)


# ── Convenience Functions ────────────────────────────────────────────────────

def log_exception(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """Log an exception with full traceback.

    Args:
        logger: The logger to use.
        error: The exception that was caught.
        context: Additional context about where the error occurred.
    """
    if context:
        logger.error("%s: %s", context, error, exc_info=True)
    else:
        logger.error("Unexpected error: %s", error, exc_info=True)
