"""
LogDot Log Capture - Intercepts Python logging and print() output.

Provides a logging.Handler that forwards stdlib logging records to LogDot,
and a stdout/stderr wrapper that captures print() calls.

Usage:
    from logdot.capture import LogdotLoggingHandler, enable_print_capture

    # Capture stdlib logging
    import logging
    handler = LogdotLoggingHandler(logger=logdot_logger)
    logging.root.addHandler(handler)

    # Capture print()
    enable_print_capture(logger=logdot_logger)
"""

import io
import logging
import sys
import threading
from typing import Any, Dict, Optional

_MAX_MESSAGE_BYTES = 16000


def _truncate(message: str, max_bytes: int = _MAX_MESSAGE_BYTES) -> str:
    encoded = message.encode("utf-8")
    if len(encoded) <= max_bytes:
        return message
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "... [truncated]"


_LEVEL_MAP = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}


class LogdotLoggingHandler(logging.Handler):
    """
    A logging.Handler that forwards log records to LogDot.

    Attach to the root logger to capture all logging output:

        import logging
        handler = LogdotLoggingHandler(logger=logdot_logger)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.DEBUG)
    """

    def __init__(self, logger: Any) -> None:
        super().__init__()
        self._logger = logger
        self._sending = threading.local()

    def emit(self, record: logging.LogRecord) -> None:
        # Guard against recursion: LogDotLogger uses requests which
        # may trigger urllib3 debug logging
        if getattr(self._sending, "active", False):
            return

        try:
            self._sending.active = True
            message = _truncate(self.format(record))
            severity = _LEVEL_MAP.get(record.levelno, "info")

            tags: Dict[str, Any] = {
                "logger_name": record.name,
                "source": "python_logging",
            }

            if record.pathname:
                tags["pathname"] = record.pathname
            if record.lineno is not None:
                tags["lineno"] = record.lineno
            if record.funcName:
                tags["func_name"] = record.funcName

            if record.exc_info and record.exc_info[1]:
                exc = record.exc_info[1]
                tags["exception_type"] = type(exc).__name__
                tags["exception_message"] = str(exc)[:1000]

            log_fn = getattr(self._logger, severity, self._logger.info)
            log_fn(message, tags)
        except Exception:
            pass
        finally:
            self._sending.active = False


class _CapturedStream(io.TextIOBase):
    """
    A stream wrapper that intercepts writes (print() calls)
    and forwards them to LogDot while still writing to the original stream.
    """

    def __init__(self, original: Any, logger: Any, severity: str) -> None:
        self._original = original
        self._logger = logger
        self._severity = severity
        self._sending = threading.local()

    def write(self, text: str) -> int:
        result = self._original.write(text)

        # Skip empty/whitespace-only writes
        stripped = text.strip()
        if not stripped:
            return result

        if getattr(self._sending, "active", False):
            return result

        try:
            self._sending.active = True
            message = _truncate(stripped)
            log_fn = getattr(self._logger, self._severity, self._logger.info)
            log_fn(message, {"source": "print"})
        except Exception:
            pass
        finally:
            self._sending.active = False

        return result

    def flush(self) -> None:
        self._original.flush()

    def fileno(self) -> int:
        return self._original.fileno()

    @property
    def encoding(self) -> str:
        return getattr(self._original, "encoding", "utf-8")

    def isatty(self) -> bool:
        return self._original.isatty()

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True


# Module-level references to originals so we can restore
_original_stdout: Optional[Any] = None
_original_stderr: Optional[Any] = None


def enable_print_capture(logger: Any) -> None:
    """
    Replace sys.stdout and sys.stderr with wrappers that send
    print() output to LogDot.

    The original streams still receive the output (print still works normally).
    stdout goes as severity "info", stderr as "error".
    """
    global _original_stdout, _original_stderr

    _original_stdout = sys.stdout
    _original_stderr = sys.stderr

    sys.stdout = _CapturedStream(sys.stdout, logger, "info")  # type: ignore[assignment]
    sys.stderr = _CapturedStream(sys.stderr, logger, "error")  # type: ignore[assignment]


def disable_print_capture() -> None:
    """Restore original stdout and stderr."""
    global _original_stdout, _original_stderr

    if _original_stdout is not None:
        sys.stdout = _original_stdout
        _original_stdout = None
    if _original_stderr is not None:
        sys.stderr = _original_stderr
        _original_stderr = None
