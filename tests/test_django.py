"""Tests for LogDot Django middleware"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock


def make_settings(**overrides):
    """Create a mock Django settings object"""
    defaults = {
        "LOGDOT_API_KEY": "test_api_key",
        "LOGDOT_HOSTNAME": "test-service",
        "LOGDOT_DEBUG": False,
        "LOGDOT_TIMEOUT": 5000,
        "LOGDOT_ENTITY_NAME": "test-service",
        "LOGDOT_LOG_REQUESTS": True,
        "LOGDOT_LOG_METRICS": True,
        "LOGDOT_IGNORE_PATHS": [],
        "LOGDOT_CAPTURE_LOGGING": False,
    }
    defaults.update(overrides)

    settings = MagicMock()
    for key, value in defaults.items():
        setattr(settings, key, value)
    return settings


def make_request(method="GET", path="/api/users"):
    """Create a mock Django request"""
    request = MagicMock()
    request.method = method
    request.path = path
    return request


def make_response(status_code=200):
    """Create a mock Django response"""
    response = MagicMock()
    response.status_code = status_code
    return response


def _create_middleware(settings_overrides=None):
    """Create middleware with mocked Django settings and SDK classes."""
    settings = make_settings(**(settings_overrides or {}))
    mock_django_conf = MagicMock()
    mock_django_conf.settings = settings

    mock_logger_instance = MagicMock()
    mock_metrics_instance = MagicMock()
    mock_metrics_client = MagicMock()
    mock_metrics_instance.for_entity.return_value = mock_metrics_client
    mock_entity = MagicMock()
    mock_entity.id = "entity-123"
    mock_metrics_instance.get_or_create_entity.return_value = mock_entity

    with patch.dict("sys.modules", {
        "django": MagicMock(),
        "django.conf": mock_django_conf,
    }):
        with patch("logdot.logger.LogDotLogger", return_value=mock_logger_instance), \
             patch("logdot.metrics.LogDotMetrics", return_value=mock_metrics_instance):
            from logdot.django import LogdotMiddleware

            response = make_response(200)
            middleware = LogdotMiddleware(get_response=lambda r: response)

            return middleware, mock_logger_instance, mock_metrics_instance, mock_metrics_client, response


class TestLogdotMiddlewareInit:
    """Tests for middleware initialization"""

    def test_creates_logger_with_settings(self):
        """Test that middleware creates a LogDotLogger from settings"""
        middleware, mock_logger, _, _, _ = _create_middleware()
        # Logger was created (middleware has the instance)
        assert middleware._logger is mock_logger

    def test_raises_without_api_key(self):
        """Test that missing API key raises ValueError"""
        settings = make_settings(LOGDOT_API_KEY=None)
        mock_conf = MagicMock()
        mock_conf.settings = settings

        with patch.dict("sys.modules", {
            "django": MagicMock(),
            "django.conf": mock_conf,
        }):
            from logdot.django import LogdotMiddleware
            with pytest.raises(ValueError, match="LOGDOT_API_KEY"):
                LogdotMiddleware(get_response=lambda r: make_response())

    def test_raises_without_hostname(self):
        """Test that missing hostname raises ValueError"""
        settings = make_settings(LOGDOT_HOSTNAME=None)
        mock_conf = MagicMock()
        mock_conf.settings = settings

        with patch.dict("sys.modules", {
            "django": MagicMock(),
            "django.conf": mock_conf,
        }):
            from logdot.django import LogdotMiddleware
            with pytest.raises(ValueError, match="LOGDOT_HOSTNAME"):
                LogdotMiddleware(get_response=lambda r: make_response())


class TestLogdotMiddlewareCall:
    """Tests for middleware __call__"""

    def test_returns_response(self):
        """Test that middleware returns the response from get_response"""
        middleware, _, _, _, expected_response = _create_middleware()
        request = make_request()
        result = middleware(request)
        assert result is expected_response

    def test_logs_request_as_info_for_2xx(self):
        """Test that 2xx responses are logged as info"""
        middleware, mock_logger, _, _, _ = _create_middleware()
        middleware(make_request("GET", "/api/users"))

        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "GET" in msg
        assert "/api/users" in msg
        assert "200" in msg

    def test_logs_request_as_warn_for_4xx(self):
        """Test that 4xx responses are logged as warn"""
        settings = make_settings()
        mock_conf = MagicMock()
        mock_conf.settings = settings
        mock_logger = MagicMock()

        with patch.dict("sys.modules", {
            "django": MagicMock(),
            "django.conf": mock_conf,
        }):
            with patch("logdot.logger.LogDotLogger", return_value=mock_logger), \
                 patch("logdot.metrics.LogDotMetrics"):
                from logdot.django import LogdotMiddleware
                response = make_response(404)
                middleware = LogdotMiddleware(get_response=lambda r: response)
                middleware(make_request())
                mock_logger.warn.assert_called_once()

    def test_logs_request_as_error_for_5xx(self):
        """Test that 5xx responses are logged as error"""
        settings = make_settings()
        mock_conf = MagicMock()
        mock_conf.settings = settings
        mock_logger = MagicMock()

        with patch.dict("sys.modules", {
            "django": MagicMock(),
            "django.conf": mock_conf,
        }):
            with patch("logdot.logger.LogDotLogger", return_value=mock_logger), \
                 patch("logdot.metrics.LogDotMetrics"):
                from logdot.django import LogdotMiddleware
                response = make_response(500)
                middleware = LogdotMiddleware(get_response=lambda r: response)
                middleware(make_request())
                mock_logger.error.assert_called_once()

    def test_includes_tags_in_log(self):
        """Test that log tags contain HTTP metadata"""
        middleware, mock_logger, _, _, _ = _create_middleware()
        middleware(make_request("POST", "/api/orders"))

        tags = mock_logger.info.call_args[0][1]
        assert tags["http_method"] == "POST"
        assert tags["http_path"] == "/api/orders"
        assert tags["http_status"] == 200
        assert "duration_ms" in tags
        assert tags["source"] == "django_middleware"

    def test_skips_ignored_paths(self):
        """Test that requests to ignored paths are not logged"""
        middleware, mock_logger, _, _, _ = _create_middleware(
            settings_overrides={"LOGDOT_IGNORE_PATHS": ["/health"]}
        )
        middleware(make_request("GET", "/health"))
        mock_logger.info.assert_not_called()

    def test_respects_log_requests_false(self):
        """Test that request logging can be disabled"""
        middleware, mock_logger, _, _, _ = _create_middleware(
            settings_overrides={"LOGDOT_LOG_REQUESTS": False}
        )
        middleware(make_request())
        mock_logger.info.assert_not_called()

    def test_sends_duration_metric(self):
        """Test that duration metric is sent"""
        middleware, _, _, mock_metrics_client, _ = _create_middleware()
        middleware(make_request("GET", "/api/users"))

        mock_metrics_client.send.assert_called_once()
        args = mock_metrics_client.send.call_args
        assert args[0][0] == "http.request.duration"
        assert args[0][2] == "ms"

    def test_respects_log_metrics_false(self):
        """Test that metrics can be disabled"""
        middleware, _, mock_metrics, _, _ = _create_middleware(
            settings_overrides={"LOGDOT_LOG_METRICS": False}
        )
        middleware(make_request())
        # No entity lookup should have happened
        mock_metrics.get_or_create_entity.assert_not_called()


class TestLogdotMiddlewareExceptions:
    """Tests for process_exception"""

    def test_logs_exception(self):
        """Test that unhandled exceptions are logged"""
        middleware, mock_logger, _, _, _ = _create_middleware()
        request = make_request("POST", "/api/orders")
        exc = ValueError("bad value")

        result = middleware.process_exception(request, exc)

        assert result is None
        mock_logger.error.assert_called_once()
        msg = mock_logger.error.call_args[0][0]
        assert "ValueError" in msg
        tags = mock_logger.error.call_args[0][1]
        assert tags["exception_type"] == "ValueError"
        assert tags["exception_message"] == "bad value"
        assert tags["http_method"] == "POST"
        assert tags["http_path"] == "/api/orders"

    def test_process_exception_does_not_raise(self):
        """Test that process_exception never raises"""
        middleware, mock_logger, _, _, _ = _create_middleware()
        mock_logger.error.side_effect = RuntimeError("SDK error")

        # Should not raise
        middleware.process_exception(make_request(), ValueError("test"))
