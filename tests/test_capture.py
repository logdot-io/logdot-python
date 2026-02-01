"""Tests for LogDot log capture (logging handler and print capture)"""

import io
import logging
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, call

from logdot.capture import (
    LogdotLoggingHandler,
    enable_print_capture,
    disable_print_capture,
    _truncate,
    _CapturedStream,
)


class TestLogdotLoggingHandler:
    """Tests for LogdotLoggingHandler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_logger = MagicMock()
        self.handler = LogdotLoggingHandler(logger=self.mock_logger)
        self.handler.setFormatter(logging.Formatter("%(message)s"))

    def test_forwards_info_record_to_logdot(self):
        """Test that INFO records are forwarded as info severity"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="test message",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        self.mock_logger.info.assert_called_once()
        args = self.mock_logger.info.call_args
        assert args[0][0] == "test message"

    def test_forwards_error_record_to_logdot(self):
        """Test that ERROR records are forwarded as error severity"""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="error message",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        self.mock_logger.error.assert_called_once()

    def test_forwards_warning_record_as_warn(self):
        """Test that WARNING records are forwarded as warn severity"""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="warning message",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        self.mock_logger.warn.assert_called_once()

    def test_forwards_debug_record_to_logdot(self):
        """Test that DEBUG records are forwarded as debug severity"""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=10,
            msg="debug message",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        self.mock_logger.debug.assert_called_once()

    def test_forwards_critical_as_error(self):
        """Test that CRITICAL records are forwarded as error severity"""
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=10,
            msg="critical message",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        self.mock_logger.error.assert_called_once()

    def test_includes_logger_name_in_tags(self):
        """Test that logger name is included in tags"""
        record = logging.LogRecord(
            name="myapp.views",
            level=logging.INFO,
            pathname="views.py",
            lineno=42,
            msg="test",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        tags = self.mock_logger.info.call_args[0][1]
        assert tags["logger_name"] == "myapp.views"
        assert tags["source"] == "python_logging"

    def test_includes_file_info_in_tags(self):
        """Test that file path and line number are included"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/views.py",
            lineno=42,
            msg="test",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        tags = self.mock_logger.info.call_args[0][1]
        assert tags["pathname"] == "/app/views.py"
        assert tags["lineno"] == 42

    def test_includes_lineno_zero(self):
        """Test that lineno 0 is included (not treated as falsy)"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )

        self.handler.emit(record)

        tags = self.mock_logger.info.call_args[0][1]
        assert tags["lineno"] == 0

    def test_includes_exception_info_in_tags(self):
        """Test that exception info is included when present"""
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="error occurred",
            args=None,
            exc_info=exc_info,
        )

        self.handler.emit(record)

        tags = self.mock_logger.error.call_args[0][1]
        assert tags["exception_type"] == "ValueError"
        assert tags["exception_message"] == "test error"

    def test_prevents_recursion(self):
        """Test that re-entrant calls are skipped"""
        call_count = 0

        def side_effect(msg, tags):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate re-entrant logging from inside the SDK
                record = logging.LogRecord(
                    name="urllib3",
                    level=logging.DEBUG,
                    pathname="",
                    lineno=0,
                    msg="re-entrant log",
                    args=None,
                    exc_info=None,
                )
                self.handler.emit(record)

        self.mock_logger.info.side_effect = side_effect

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="original",
            args=None,
            exc_info=None,
        )
        self.handler.emit(record)

        # Only 1 call, not 2 (re-entrant call was skipped)
        assert call_count == 1

    def test_swallows_exceptions(self):
        """Test that exceptions in the handler don't propagate"""
        self.mock_logger.info.side_effect = RuntimeError("SDK error")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="test",
            args=None,
            exc_info=None,
        )

        # Should not raise
        self.handler.emit(record)


class TestPrintCapture:
    """Tests for enable_print_capture / disable_print_capture"""

    def setup_method(self):
        """Save originals"""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def teardown_method(self):
        """Always restore originals"""
        disable_print_capture()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def test_wraps_stdout(self):
        """Test that enable_print_capture replaces sys.stdout"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)

        assert isinstance(sys.stdout, _CapturedStream)

    def test_wraps_stderr(self):
        """Test that enable_print_capture replaces sys.stderr"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)

        assert isinstance(sys.stderr, _CapturedStream)

    def test_disable_restores_stdout(self):
        """Test that disable_print_capture restores sys.stdout"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)
        disable_print_capture()

        assert sys.stdout is self.original_stdout

    def test_disable_restores_stderr(self):
        """Test that disable_print_capture restores sys.stderr"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)
        disable_print_capture()

        assert sys.stderr is self.original_stderr

    def test_captures_stdout_writes_as_info(self):
        """Test that stdout writes are sent to LogDot as info"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)

        sys.stdout.write("hello world")

        mock_logger.info.assert_called_once()
        args = mock_logger.info.call_args[0]
        assert args[0] == "hello world"
        assert args[1] == {"source": "print"}

    def test_captures_stderr_writes_as_error(self):
        """Test that stderr writes are sent to LogDot as error"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)

        sys.stderr.write("error output")

        mock_logger.error.assert_called_once()

    def test_skips_whitespace_only_writes(self):
        """Test that empty/whitespace writes are not captured"""
        mock_logger = MagicMock()
        enable_print_capture(logger=mock_logger)

        sys.stdout.write("\n")
        sys.stdout.write("   ")
        sys.stdout.write("")

        mock_logger.info.assert_not_called()

    def test_preserves_original_output(self):
        """Test that original stream still receives output"""
        mock_logger = MagicMock()
        original_write = self.original_stdout.write

        enable_print_capture(logger=mock_logger)
        # The wrapped stream should write to the original
        result = sys.stdout.write("test")

        assert isinstance(result, int)

    def test_disable_is_idempotent(self):
        """Test that calling disable_print_capture twice is safe"""
        disable_print_capture()
        disable_print_capture()

        assert sys.stdout is self.original_stdout


class TestTruncate:
    """Tests for the _truncate utility function"""

    def test_returns_short_strings_unchanged(self):
        """Test that short strings pass through"""
        assert _truncate("hello") == "hello"

    def test_truncates_long_strings(self):
        """Test that strings exceeding max_bytes are truncated"""
        long_str = "x" * 20000
        result = _truncate(long_str, max_bytes=100)

        assert len(result.encode("utf-8")) < 20000
        assert result.endswith("... [truncated]")

    def test_handles_multibyte_characters(self):
        """Test that truncation handles UTF-8 correctly"""
        # Each emoji is 4 bytes in UTF-8
        emoji_str = "\U0001F600" * 5000
        result = _truncate(emoji_str, max_bytes=100)

        # Should be valid UTF-8
        result.encode("utf-8")
        assert result.endswith("... [truncated]")
