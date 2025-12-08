"""Tests for LogDotLogger"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from logdot import LogDotLogger, LogLevel


class TestLogDotLogger:
    """Tests for LogDotLogger class"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.logger.HttpClient'):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service'
            )

    def test_constructor_creates_logger(self):
        """Test that constructor creates a logger with required config"""
        assert self.logger.get_hostname() == 'test-service'

    def test_constructor_initializes_empty_context(self):
        """Test that logger starts with empty context"""
        assert self.logger.get_context() == {}

    def test_constructor_accepts_initial_context(self):
        """Test that constructor accepts initial context"""
        with patch('logdot.logger.HttpClient'):
            logger = LogDotLogger(
                api_key='test',
                hostname='test',
                _context={'env': 'production'}
            )
        assert logger.get_context() == {'env': 'production'}


class TestWithContext:
    """Tests for with_context method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.logger.HttpClient'):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service'
            )

    def test_creates_new_logger_with_context(self):
        """Test that with_context creates a new logger with merged context"""
        context_logger = self.logger.with_context({'user_id': 123})

        assert context_logger.get_context() == {'user_id': 123}
        # Original should be unchanged
        assert self.logger.get_context() == {}

    def test_merges_contexts_when_chained(self):
        """Test that chained contexts are merged"""
        logger1 = self.logger.with_context({'user_id': 123})
        logger2 = logger1.with_context({'request_id': 'abc'})

        assert logger2.get_context() == {'user_id': 123, 'request_id': 'abc'}

    def test_allows_overwriting_context_values(self):
        """Test that new context can overwrite existing values"""
        logger1 = self.logger.with_context({'env': 'dev'})
        logger2 = logger1.with_context({'env': 'prod'})

        assert logger2.get_context() == {'env': 'prod'}


class TestGetContext:
    """Tests for get_context method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.logger.HttpClient'):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service',
                _context={'key': 'value'}
            )

    def test_returns_copy_of_context(self):
        """Test that get_context returns a copy"""
        context = self.logger.get_context()
        context['key'] = 'modified'

        # Original should be unchanged
        assert self.logger.get_context() == {'key': 'value'}


class TestBatchOperations:
    """Tests for batch operations"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.logger.HttpClient'):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service'
            )

    def test_starts_with_empty_batch(self):
        """Test that logger starts with no batch"""
        assert self.logger.get_batch_size() == 0

    def test_queues_logs_in_batch_mode(self):
        """Test that logs are queued in batch mode"""
        self.logger.begin_batch()
        self.logger.info('message 1')
        self.logger.info('message 2')

        assert self.logger.get_batch_size() == 2

    def test_clears_batch_on_end_batch(self):
        """Test that end_batch clears the queue"""
        self.logger.begin_batch()
        self.logger.info('message 1')
        assert self.logger.get_batch_size() == 1

        self.logger.end_batch()
        assert self.logger.get_batch_size() == 0

    def test_clear_batch_keeps_batch_mode(self):
        """Test that clear_batch doesn't exit batch mode"""
        self.logger.begin_batch()
        self.logger.info('message 1')
        self.logger.clear_batch()

        assert self.logger.get_batch_size() == 0

        # Should still be in batch mode
        self.logger.info('message 2')
        assert self.logger.get_batch_size() == 1


class TestLogMethods:
    """Tests for log methods"""

    def setup_method(self):
        """Set up test fixtures"""
        mock_http = MagicMock()
        mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.logger.HttpClient', return_value=mock_http):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service'
            )
            self.mock_http = mock_http

    def test_debug_method(self):
        """Test debug logging"""
        result = self.logger.debug('debug message')
        assert result is True

    def test_info_method(self):
        """Test info logging"""
        result = self.logger.info('info message')
        assert result is True

    def test_warn_method(self):
        """Test warn logging"""
        result = self.logger.warn('warn message')
        assert result is True

    def test_error_method(self):
        """Test error logging"""
        result = self.logger.error('error message')
        assert result is True

    def test_log_with_tags(self):
        """Test logging with tags"""
        result = self.logger.info('message', {'tag_key': 'tag_value'})
        assert result is True


class TestMergeTags:
    """Tests for tag merging behavior"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.logger.HttpClient'):
            self.logger = LogDotLogger(
                api_key='test_api_key',
                hostname='test-service'
            )

    def test_context_merged_with_tags(self):
        """Test that context is merged with tags when logging"""
        context_logger = self.logger.with_context({'service': 'api', 'env': 'prod'})

        # The merge happens internally during log()
        # We verify the context is set correctly
        assert context_logger.get_context() == {'service': 'api', 'env': 'prod'}

    def test_tags_override_context(self):
        """Test that tags can override context values"""
        context_logger = self.logger.with_context({'env': 'dev'})

        # When logging with {'env': 'prod'}, it should override
        # This is tested by verifying the internal _merge_tags behavior
        merged = context_logger._merge_tags({'env': 'prod'})
        assert merged == {'env': 'prod'}

    def test_merge_with_none_tags(self):
        """Test merging when no tags provided"""
        context_logger = self.logger.with_context({'key': 'value'})
        merged = context_logger._merge_tags(None)
        assert merged == {'key': 'value'}

    def test_merge_with_empty_context_and_none_tags(self):
        """Test merging with empty context and no tags"""
        merged = self.logger._merge_tags(None)
        assert merged is None
