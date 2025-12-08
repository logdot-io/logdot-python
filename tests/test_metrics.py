"""Tests for LogDotMetrics and BoundMetricsClient"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from logdot import LogDotMetrics
from logdot.metrics import BoundMetricsClient


class TestLogDotMetrics:
    """Tests for LogDotMetrics class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(
            status=200,
            data={'data': {'id': 'entity-uuid-123'}}
        )
        self.mock_http.get.return_value = Mock(
            status=200,
            data={'data': {'id': 'entity-uuid-123', 'name': 'test-entity'}}
        )

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')

    def test_constructor_creates_metrics_client(self):
        """Test that constructor creates a metrics client"""
        assert self.metrics is not None


class TestCreateEntity:
    """Tests for create_entity method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(
            status=200,
            data={'data': {'id': 'entity-uuid-123'}}
        )

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')

    def test_creates_entity_and_returns_it(self):
        """Test that create_entity creates an entity and returns it"""
        entity = self.metrics.create_entity(
            name='test-service',
            description='Test service description'
        )

        assert entity is not None
        assert entity.name == 'test-service'
        assert entity.id == 'entity-uuid-123'

    def test_accepts_metadata(self):
        """Test that create_entity accepts metadata"""
        entity = self.metrics.create_entity(
            name='test-service',
            description='Test',
            metadata={'version': '1.0.0', 'region': 'us-east-1'}
        )

        assert entity is not None


class TestGetEntityByName:
    """Tests for get_entity_by_name method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.get.return_value = Mock(
            status=200,
            data={'data': {'id': 'entity-uuid-123', 'name': 'test-service'}}
        )

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')

    def test_finds_entity_by_name(self):
        """Test that get_entity_by_name finds an entity"""
        entity = self.metrics.get_entity_by_name('test-service')

        assert entity is not None
        assert entity.id == 'entity-uuid-123'


class TestGetOrCreateEntity:
    """Tests for get_or_create_entity method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.get.return_value = Mock(
            status=200,
            data={'data': {'id': 'entity-uuid-123', 'name': 'test-service'}}
        )
        self.mock_http.post.return_value = Mock(
            status=200,
            data={'data': {'id': 'new-entity-uuid'}}
        )

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')

    def test_returns_existing_entity_if_found(self):
        """Test that get_or_create_entity returns existing entity"""
        entity = self.metrics.get_or_create_entity(name='test-service')

        assert entity is not None
        assert entity.id == 'entity-uuid-123'


class TestForEntity:
    """Tests for for_entity method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('logdot.metrics.HttpClient'):
            self.metrics = LogDotMetrics(api_key='test_api_key')

    def test_returns_bound_metrics_client(self):
        """Test that for_entity returns a BoundMetricsClient"""
        client = self.metrics.for_entity('entity-uuid-123')

        assert isinstance(client, BoundMetricsClient)
        assert client.get_entity_id() == 'entity-uuid-123'


class TestBoundMetricsClientGetEntityId:
    """Tests for BoundMetricsClient.get_entity_id method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_returns_bound_entity_id(self):
        """Test that get_entity_id returns the bound entity ID"""
        assert self.client.get_entity_id() == 'entity-uuid-123'


class TestBoundMetricsClientSend:
    """Tests for BoundMetricsClient.send method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_sends_a_metric(self):
        """Test that send sends a metric"""
        result = self.client.send('cpu.usage', 45.5, 'percent')
        assert result is True

    def test_sends_metric_with_tags(self):
        """Test that send accepts tags"""
        result = self.client.send(
            'response_time', 123, 'ms',
            tags={'endpoint': '/api/users', 'method': 'GET'}
        )
        assert result is True

    def test_fails_in_batch_mode(self):
        """Test that send fails in batch mode"""
        self.client.begin_batch('temperature', 'celsius')
        result = self.client.send('cpu', 50, 'percent')
        assert result is False


class TestBoundMetricsClientSingleBatch:
    """Tests for single-metric batch operations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_queues_values_in_batch_mode(self):
        """Test that values are queued in batch mode"""
        self.client.begin_batch('temperature', 'celsius')
        self.client.add(23.5)
        self.client.add(24.0)
        self.client.add(23.8)

        assert self.client.get_batch_size() == 3

    def test_clears_batch_on_end_batch(self):
        """Test that end_batch clears the queue"""
        self.client.begin_batch('temperature', 'celsius')
        self.client.add(23.5)
        self.client.end_batch()

        assert self.client.get_batch_size() == 0

    def test_fails_to_add_when_not_in_batch_mode(self):
        """Test that add fails when not in batch mode"""
        result = self.client.add(23.5)
        assert result is False


class TestBoundMetricsClientMultiBatch:
    """Tests for multi-metric batch operations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_queues_different_metrics_in_multi_batch_mode(self):
        """Test that different metrics can be queued in multi-batch mode"""
        self.client.begin_multi_batch()
        self.client.add_metric('cpu', 45, 'percent')
        self.client.add_metric('memory', 2048, 'MB')
        self.client.add_metric('disk', 50, 'GB')

        assert self.client.get_batch_size() == 3

    def test_fails_to_add_metric_when_not_in_multi_batch_mode(self):
        """Test that add_metric fails when not in multi-batch mode"""
        result = self.client.add_metric('cpu', 45, 'percent')
        assert result is False

    def test_fails_to_add_in_multi_batch_mode(self):
        """Test that add fails in multi-batch mode"""
        self.client.begin_multi_batch()
        result = self.client.add(45)
        assert result is False


class TestBoundMetricsClientSendBatch:
    """Tests for send_batch method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_sends_batched_metrics(self):
        """Test that send_batch sends all queued metrics"""
        self.client.begin_batch('temperature', 'celsius')
        self.client.add(23.5)
        self.client.add(24.0)

        result = self.client.send_batch()
        assert result is True
        assert self.client.get_batch_size() == 0

    def test_returns_false_for_empty_batch(self):
        """Test that send_batch returns False for empty batch"""
        self.client.begin_batch('temperature', 'celsius')
        result = self.client.send_batch()
        assert result is False


class TestBoundMetricsClientClearBatch:
    """Tests for clear_batch method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_clears_without_sending(self):
        """Test that clear_batch clears without sending"""
        self.client.begin_batch('temperature', 'celsius')
        self.client.add(23.5)
        self.client.clear_batch()

        assert self.client.get_batch_size() == 0


class TestBoundMetricsClientErrorTracking:
    """Tests for error tracking"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_http = MagicMock()
        self.mock_http.post.return_value = Mock(status=200, data={})

        with patch('logdot.metrics.HttpClient', return_value=self.mock_http):
            self.metrics = LogDotMetrics(api_key='test_api_key')
            self.client = self.metrics.for_entity('entity-uuid-123')

    def test_tracks_last_error(self):
        """Test that last error is tracked"""
        self.client.add(23.5)  # Should fail - not in batch mode
        assert 'batch mode' in self.client.get_last_error()

    def test_starts_with_empty_error(self):
        """Test that client starts with default HTTP code"""
        assert self.client.get_last_http_code() == -1
