"""
HTTP Client with retry logic and exponential backoff
"""

import random
import time
from typing import Any, Callable, Dict, Optional, TypeVar

import requests

from logdot.types import HttpResponse, RetryConfig

# Base URLs for LogDot API
BASE_LOGS_URL = "https://logs.logdot.io/api/v1"
BASE_METRICS_URL = "https://metrics.logdot.io/api/v1"

T = TypeVar("T")


class HttpClient:
    """HTTP Client for LogDot API with automatic retry and exponential backoff"""

    def __init__(
        self,
        api_key: str,
        timeout: int = 5000,
        debug: bool = False,
        retry_config: Optional[RetryConfig] = None,
    ):
        self._api_key = api_key
        self._timeout = timeout / 1000  # Convert to seconds
        self._debug = debug
        self._retry_config = retry_config or RetryConfig()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
        )

    def post(self, url: str, body: Dict[str, Any]) -> HttpResponse:
        """Perform a POST request with retry logic"""
        return self._execute_with_retry(lambda: self._do_post(url, body))

    def get(self, url: str) -> HttpResponse:
        """Perform a GET request with retry logic"""
        return self._execute_with_retry(lambda: self._do_get(url))

    def _do_post(self, url: str, body: Dict[str, Any]) -> HttpResponse:
        """Execute POST request"""
        self._log(f"POST {url}")
        self._log(f"Payload: {body}")

        response = self._session.post(url, json=body, timeout=self._timeout)
        data = None
        if response.text:
            try:
                data = response.json()
            except ValueError:
                pass

        self._log(f"Response status: {response.status_code}")
        if data:
            self._log(f"Response body: {data}")

        return HttpResponse(status=response.status_code, data=data)

    def _do_get(self, url: str) -> HttpResponse:
        """Execute GET request"""
        self._log(f"GET {url}")

        response = self._session.get(url, timeout=self._timeout)
        data = None
        if response.text:
            try:
                data = response.json()
            except ValueError:
                pass

        self._log(f"Response status: {response.status_code}")

        return HttpResponse(status=response.status_code, data=data)

    def _execute_with_retry(self, fn: Callable[[], HttpResponse]) -> HttpResponse:
        """Execute a function with exponential backoff retry"""
        last_error: Optional[Exception] = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                return fn()
            except requests.RequestException as e:
                last_error = e

                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff(attempt)
                    self._log(
                        f"Retry {attempt + 1}/{self._retry_config.max_attempts} "
                        f"after {delay}ms - Error: {e}"
                    )
                    time.sleep(delay / 1000)

        raise last_error  # type: ignore

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with jitter"""
        delay = self._retry_config.base_delay_ms * (2**attempt)
        jitter = random.random() * 0.3 * delay  # 30% jitter
        return min(delay + jitter, self._retry_config.max_delay_ms)

    def _log(self, message: str) -> None:
        """Log debug message"""
        if self._debug:
            print(f"[LogDot] {message}")

    def close(self) -> None:
        """Close the HTTP session"""
        self._session.close()
