"""
LogDot Logger - Handles log transmission to LogDot cloud

Example:
    from logdot import LogDotLogger

    logger = LogDotLogger(
        api_key='ilog_live_YOUR_API_KEY',
        hostname='my-service',
    )

    await logger.info('Application started')
    await logger.error('Something went wrong', {'error_code': 500})

    # Context-aware logging
    user_logger = logger.with_context({'user_id': 123})
    user_logger.info('User action')  # Includes user_id automatically
"""

from typing import Any, Dict, List, Optional, Union

from logdot.http import BASE_LOGS_URL, HttpClient
from logdot.types import LoggerConfig, LogEntry, LogLevel, RetryConfig

# API endpoints
ENDPOINT_SINGLE = "/logs"
ENDPOINT_BATCH = "/logs/batch"


class LogDotLogger:
    """
    LogDot Logger class for sending logs to LogDot cloud.

    Example:
        logger = LogDotLogger(api_key='ilog_live_YOUR_API_KEY', hostname='my-service')
        logger.info('Hello, world!')
        logger.error('Something went wrong', {'error_code': 500})
    """

    def __init__(
        self,
        api_key: str,
        hostname: str,
        timeout: int = 5000,
        retry_attempts: int = 3,
        retry_delay_ms: int = 1000,
        retry_max_delay_ms: int = 30000,
        debug: bool = False,
        _context: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a new LogDot Logger.

        Args:
            api_key: API key for authentication (format: ilog_live_XXXXX)
            hostname: Hostname identifier for logs
            timeout: HTTP request timeout in milliseconds (default: 5000)
            retry_attempts: Maximum retry attempts for failed requests (default: 3)
            retry_delay_ms: Base delay in milliseconds for exponential backoff (default: 1000)
            retry_max_delay_ms: Maximum delay in milliseconds for exponential backoff (default: 30000)
            debug: Enable debug output to console (default: False)
        """
        self._api_key = api_key
        self._hostname = hostname
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._retry_delay_ms = retry_delay_ms
        self._retry_max_delay_ms = retry_max_delay_ms
        self._debug_enabled = debug

        self._http = HttpClient(
            api_key=api_key,
            timeout=timeout,
            debug=debug,
            retry_config=RetryConfig(
                max_attempts=retry_attempts,
                base_delay_ms=retry_delay_ms,
                max_delay_ms=retry_max_delay_ms,
            ),
        )
        self._batch_mode = False
        self._batch_queue: List[LogEntry] = []
        self._context: Dict[str, Any] = _context or {}

    def with_context(self, context: Dict[str, Any]) -> "LogDotLogger":
        """
        Create a new logger with additional context that will be merged with all log tags.

        Args:
            context: Dictionary containing key-value pairs to add to all logs

        Returns:
            A new LogDotLogger instance with the merged context

        Example:
            logger = LogDotLogger(api_key='...', hostname='my-service')
            user_logger = logger.with_context({'user_id': 123, 'session_id': 'abc'})
            user_logger.info('User action')  # Will include user_id and session_id
        """
        merged_context = {**self._context, **context}
        return LogDotLogger(
            api_key=self._api_key,
            hostname=self._hostname,
            timeout=self._timeout,
            retry_attempts=self._retry_attempts,
            retry_delay_ms=self._retry_delay_ms,
            retry_max_delay_ms=self._retry_max_delay_ms,
            debug=self._debug_enabled,
            _context=merged_context,
        )

    def get_context(self) -> Dict[str, Any]:
        """Get the current context"""
        return dict(self._context)

    def _merge_tags(self, tags: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Merge context with provided tags (tags take precedence)"""
        if not self._context and not tags:
            return None
        return {**self._context, **(tags or {})}

    def debug(self, message: str, tags: Optional[Dict[str, Any]] = None) -> bool:
        """Send a debug level log"""
        return self.log(LogLevel.DEBUG, message, tags)

    def info(self, message: str, tags: Optional[Dict[str, Any]] = None) -> bool:
        """Send an info level log"""
        return self.log(LogLevel.INFO, message, tags)

    def warn(self, message: str, tags: Optional[Dict[str, Any]] = None) -> bool:
        """Send a warning level log"""
        return self.log(LogLevel.WARN, message, tags)

    def error(self, message: str, tags: Optional[Dict[str, Any]] = None) -> bool:
        """Send an error level log"""
        return self.log(LogLevel.ERROR, message, tags)

    def log(
        self, level: LogLevel, message: str, tags: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a log at the specified level"""
        merged_tags = self._merge_tags(tags)
        entry = LogEntry(message=message, level=level, tags=merged_tags)

        if self._batch_mode:
            self._batch_queue.append(entry)
            return True

        return self._send_log(entry)

    def begin_batch(self) -> None:
        """Begin batch mode - logs will be queued instead of sent immediately"""
        self._batch_mode = True
        self.clear_batch()

    def send_batch(self) -> bool:
        """Send all queued logs in a single batch request"""
        if not self._batch_mode or not self._batch_queue:
            return False

        try:
            logs = []
            for entry in self._batch_queue:
                log_data: Dict[str, Any] = {
                    "message": entry.message,
                    "severity": entry.level.value,
                }
                if entry.tags:
                    log_data["tags"] = entry.tags
                logs.append(log_data)

            payload = {
                "hostname": self._hostname,
                "logs": logs,
            }

            url = f"{BASE_LOGS_URL}{ENDPOINT_BATCH}"
            response = self._http.post(url, payload)

            if response.status in (200, 201):
                self.clear_batch()
                return True

            self._debug_log(f"Failed to send batch. HTTP code: {response.status}")
            return False
        except Exception as e:
            self._debug_log(f"Failed to send batch: {e}")
            return False

    def end_batch(self) -> None:
        """End batch mode and clear the queue"""
        self._batch_mode = False
        self.clear_batch()

    def clear_batch(self) -> None:
        """Clear the batch queue without sending"""
        self._batch_queue = []

    def get_batch_size(self) -> int:
        """Get the current batch queue size"""
        return len(self._batch_queue)

    def get_hostname(self) -> str:
        """Get the configured hostname"""
        return self._hostname

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable debug output"""
        self._debug_enabled = enabled

    def _send_log(self, entry: LogEntry) -> bool:
        """Send a single log entry"""
        try:
            payload: Dict[str, Any] = {
                "message": entry.message,
                "severity": entry.level.value,
                "hostname": self._hostname,
            }

            if entry.tags:
                payload["tags"] = entry.tags

            url = f"{BASE_LOGS_URL}{ENDPOINT_SINGLE}"
            response = self._http.post(url, payload)

            if response.status in (200, 201):
                return True

            self._debug_log(f"Failed to send log. HTTP code: {response.status}")
            return False
        except Exception as e:
            self._debug_log(f"Failed to send log: {e}")
            return False

    def _debug_log(self, message: str) -> None:
        """Log debug message to console"""
        if self._debug_enabled:
            print(f"[LogDotLogger] {message}")
