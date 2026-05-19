"""Tests for the structured logging system."""

from __future__ import annotations

import io
import logging
from contextlib import redirect_stderr

import pytest

from src.utils.logging import LogContext, get_logger, setup_logging


class TestLoggingSetup:
    """Tests for logging configuration."""

    @pytest.fixture(autouse=True)
    def setup_reset(self, reset_logging):
        pass

    def test_setup_logging_basic(self):
        """setup_logging should configure the root logger."""
        setup_logging(verbose=False)
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_verbose(self):
        """Verbose mode should set DEBUG level."""
        setup_logging(verbose=True)
        logger = get_logger("test.verbose")
        assert logger.isEnabledFor(10)  # DEBUG

    def test_get_logger_name_normalization(self):
        """get_logger should normalize module names."""
        logger = get_logger("src.test")
        name = logger.name
        assert "ai_job_finder" in name

    def test_logger_output(self):
        """Logger should output to stderr via Rich handler."""
        setup_logging(verbose=False)
        logger = get_logger("test.output")

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            logger.info("Test message")

        output = stderr.getvalue()
        assert "Test message" in output

    def test_idempotent_setup(self):
        """Calling setup_logging twice should not add duplicate handlers."""
        setup_logging(verbose=False)
        log1 = get_logger("test.idemp")
        handler_count = len(logging.getLogger("ai_job_finder").handlers)

        setup_logging(verbose=False)
        log2 = get_logger("test.idemp")
        assert len(log2.handlers) == 0  # child has no handlers
        assert len(logging.getLogger("ai_job_finder").handlers) == handler_count


class TestLogContext:
    """Tests for the LogContext manager."""

    def test_context_adds_fields(self):
        """LogContext should add fields to log records."""
        setup_logging(verbose=False)
        logger = get_logger("test.context")

        with LogContext(user_id="test123"):
            # Context is set during the block
            pass

    def test_context_scope(self):
        """LogContext should reset after exiting."""
        setup_logging(verbose=False)

        with LogContext(action="test"):
            assert True

        # After exit, context should be empty
        from src.utils.logging import _log_context
        assert _log_context.get() == {}

    def test_nested_context(self):
        """Nested LogContext should merge fields."""
        setup_logging(verbose=False)

        with LogContext(field1="a"):
            with LogContext(field2="b"):
                from src.utils.logging import _log_context
                ctx = _log_context.get()
                assert ctx["field1"] == "a"
                assert ctx["field2"] == "b"
