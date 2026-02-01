"""
LogDot Django Middleware - Automatic request logging and metrics for Django apps.

Automatically captures HTTP requests, response times, and unhandled exceptions
without any manual logging code.

Setup:
    # settings.py
    LOGDOT_API_KEY = 'ilog_live_YOUR_API_KEY'
    LOGDOT_HOSTNAME = 'my-django-app'

    MIDDLEWARE = [
        'logdot.django.LogdotMiddleware',
        # ... your other middleware
    ]

Optional settings:
    LOGDOT_ENTITY_NAME = 'my-app'      # Metrics entity name (defaults to LOGDOT_HOSTNAME)
    LOGDOT_DEBUG = False                # Enable debug output
    LOGDOT_TIMEOUT = 5000              # HTTP timeout in ms
    LOGDOT_LOG_REQUESTS = True         # Enable/disable request logging
    LOGDOT_LOG_METRICS = True          # Enable/disable duration metrics
    LOGDOT_IGNORE_PATHS = ['/health']  # Paths to skip
    LOGDOT_CAPTURE_LOGGING = False     # Forward Python logging + print() to LogDot
"""

import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Set

# Max log message size (16KB API limit with some headroom)
_MAX_MESSAGE_BYTES = 16000


def _truncate_message(message: str, max_bytes: int = _MAX_MESSAGE_BYTES) -> str:
    """Truncate a message to fit within the API's byte limit."""
    encoded = message.encode("utf-8")
    if len(encoded) <= max_bytes:
        return message
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "... [truncated]"


class LogdotMiddleware:
    """
    Django middleware that automatically logs HTTP requests, responses,
    and exceptions to LogDot.

    All logdot operations are wrapped in try/except to ensure
    the middleware never interferes with normal request handling.
    """

    def __init__(self, get_response: Callable) -> None:
        from django.conf import settings

        self.get_response = get_response

        api_key: Optional[str] = getattr(settings, "LOGDOT_API_KEY", None)
        hostname: Optional[str] = getattr(settings, "LOGDOT_HOSTNAME", None)

        if not api_key:
            raise ValueError(
                "LOGDOT_API_KEY must be set in Django settings to use LogdotMiddleware"
            )
        if not hostname:
            raise ValueError(
                "LOGDOT_HOSTNAME must be set in Django settings to use LogdotMiddleware"
            )

        debug: bool = getattr(settings, "LOGDOT_DEBUG", False)
        timeout: int = getattr(settings, "LOGDOT_TIMEOUT", 5000)
        entity_name: str = getattr(settings, "LOGDOT_ENTITY_NAME", hostname)
        self._log_requests: bool = getattr(settings, "LOGDOT_LOG_REQUESTS", True)
        self._log_metrics: bool = getattr(settings, "LOGDOT_LOG_METRICS", True)
        ignore_paths: List[str] = getattr(settings, "LOGDOT_IGNORE_PATHS", [])
        self._ignore_paths: Set[str] = set(ignore_paths)

        from logdot.logger import LogDotLogger
        from logdot.metrics import LogDotMetrics

        self._logger = LogDotLogger(
            api_key=api_key,
            hostname=hostname,
            timeout=timeout,
            debug=debug,
        )

        self._metrics: Optional[LogDotMetrics] = None
        self._metrics_client = None
        self._entity_name = entity_name
        self._entity_resolved = False
        if self._log_metrics:
            self._metrics = LogDotMetrics(
                api_key=api_key,
                timeout=timeout,
                debug=debug,
            )

        capture_logging: bool = getattr(settings, "LOGDOT_CAPTURE_LOGGING", False)
        if capture_logging:
            self._setup_log_capture()

    def _setup_log_capture(self) -> None:
        """Attach a logging handler and print capture that forward to LogDot."""
        import logging as stdlib_logging

        from logdot.capture import LogdotLoggingHandler, enable_print_capture

        handler = LogdotLoggingHandler(logger=self._logger)
        handler.setFormatter(stdlib_logging.Formatter("%(message)s"))
        stdlib_logging.root.addHandler(handler)

        enable_print_capture(logger=self._logger)

    def _ensure_entity(self) -> None:
        """Lazily resolve or create the metrics entity on first use."""
        if self._entity_resolved or not self._metrics:
            return
        try:
            entity = self._metrics.get_or_create_entity(
                name=self._entity_name,
                description=f"Django app: {self._entity_name}",
            )
            if entity:
                self._metrics_client = self._metrics.for_entity(entity.id)
                self._entity_resolved = True
        except Exception:
            pass
        # On failure, _entity_resolved stays False so next request retries

    def __call__(self, request: Any) -> Any:
        if request.path in self._ignore_paths:
            return self.get_response(request)

        start_time = time.monotonic()

        response = self.get_response(request)

        duration_ms = (time.monotonic() - start_time) * 1000

        if self._log_requests:
            self._log_request(request, response.status_code, duration_ms)

        if self._log_metrics:
            self._send_duration_metric(request, response.status_code, duration_ms)

        return response

    def process_exception(self, request: Any, exception: Exception) -> None:
        """Log unhandled exceptions. Returns None to let Django handle normally."""
        try:
            tb = traceback.format_exc()
            message = _truncate_message(
                f"Unhandled {type(exception).__name__}: {exception}"
            )
            tags: Dict[str, Any] = {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)[:1000],
                "traceback": tb[:10000],
                "http_method": request.method,
                "http_path": request.path[:500],
                "source": "django_middleware",
            }
            self._logger.error(message, tags)
        except Exception:
            pass
        return None

    def _log_request(
        self, request: Any, status_code: int, duration_ms: float
    ) -> None:
        try:
            method = request.method
            path = request.path
            message = _truncate_message(
                f"{method} {path} {status_code} ({duration_ms:.0f}ms)"
            )
            tags: Dict[str, Any] = {
                "http_method": method,
                "http_path": path[:500],
                "http_status": status_code,
                "duration_ms": round(duration_ms, 2),
                "source": "django_middleware",
            }

            if status_code >= 500:
                self._logger.error(message, tags)
            elif status_code >= 400:
                self._logger.warn(message, tags)
            else:
                self._logger.info(message, tags)
        except Exception:
            pass

    def _send_duration_metric(
        self, request: Any, status_code: int, duration_ms: float
    ) -> None:
        try:
            self._ensure_entity()
            if self._metrics_client:
                self._metrics_client.send(
                    "http.request.duration",
                    round(duration_ms, 2),
                    "ms",
                    {
                        "method": request.method,
                        "path": request.path[:500],
                        "status": str(status_code),
                    },
                )
        except Exception:
            pass
