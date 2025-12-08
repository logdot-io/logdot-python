"""
LogDot Metrics - Handles metrics transmission to LogDot cloud

Example:
    from logdot import LogDotMetrics

    # Create metrics client
    metrics = LogDotMetrics(api_key='ilog_live_YOUR_API_KEY')

    # Create or find an entity
    entity = metrics.get_or_create_entity(
        name='my-service',
        description='My production service',
    )

    # Bind to the entity for sending metrics
    client = metrics.for_entity(entity.id)

    # Send metrics
    client.send('cpu.usage', 45.5, 'percent')
    client.send('memory.used', 1024, 'MB', {'host': 'server-1'})
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from logdot.http import BASE_METRICS_URL, HttpClient
from logdot.types import Entity, CreateEntityOptions, MetricEntry, RetryConfig

# API endpoints
ENDPOINT_ENTITIES = "/entities"
ENDPOINT_ENTITIES_BY_NAME = "/entities/by-name"
ENDPOINT_SINGLE = "/metrics"
ENDPOINT_BATCH = "/metrics/batch"


def format_tags(tags: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    """Convert tags dict to list of 'key:value' strings"""
    if not tags:
        return None
    return [f"{key}:{value}" for key, value in tags.items()]


class BoundMetricsClient:
    """
    Bound metrics client for sending metrics to a specific entity.

    This class is returned by LogDotMetrics.for_entity() and should not
    be instantiated directly.
    """

    def __init__(self, http: HttpClient, entity_id: str, debug: bool = False):
        """Internal constructor - use LogDotMetrics.for_entity() instead"""
        self._http = http
        self._entity_id = entity_id
        self._debug_enabled = debug

        self._batch_mode = False
        self._multi_batch_mode = False
        self._batch_metric_name = ""
        self._batch_unit = ""
        self._batch_queue: List[MetricEntry] = []
        self._last_error = ""
        self._last_http_code = -1

    def get_entity_id(self) -> str:
        """Get the entity ID this client is bound to"""
        return self._entity_id

    def send(
        self,
        name: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a single metric"""
        if self._batch_mode:
            self._last_error = "Cannot use send() in batch mode. Use add() or add_metric() instead."
            return False

        try:
            payload: Dict[str, Any] = {
                "entity_id": self._entity_id,
                "name": name,
                "value": value,
                "unit": unit,
            }

            formatted_tags = format_tags(tags)
            if formatted_tags:
                payload["tags"] = formatted_tags

            url = f"{BASE_METRICS_URL}{ENDPOINT_SINGLE}"
            response = self._http.post(url, payload)

            self._last_http_code = response.status

            if response.status in (200, 201):
                self._last_error = ""
                return True

            self._last_error = f"HTTP {response.status}"
            return False
        except Exception as e:
            self._last_error = str(e)
            return False

    def begin_batch(self, metric_name: str, unit: str) -> None:
        """
        Begin single-metric batch mode.
        All add() calls will use the same metric name and unit.
        """
        self._batch_mode = True
        self._multi_batch_mode = False
        self._batch_metric_name = metric_name
        self._batch_unit = unit
        self.clear_batch()

    def add(self, value: float, tags: Optional[Dict[str, Any]] = None) -> bool:
        """Add a value to the single-metric batch"""
        if not self._batch_mode or self._multi_batch_mode:
            self._last_error = "Not in single-metric batch mode. Call begin_batch() first."
            return False

        self._batch_queue.append(
            MetricEntry(
                name=self._batch_metric_name,
                value=value,
                unit=self._batch_unit,
                tags=tags,
            )
        )
        return True

    def begin_multi_batch(self) -> None:
        """
        Begin multi-metric batch mode.
        Allows adding different metrics to the same batch.
        """
        self._batch_mode = True
        self._multi_batch_mode = True
        self.clear_batch()

    def add_metric(
        self,
        name: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a metric to the multi-metric batch"""
        if not self._multi_batch_mode:
            self._last_error = "Not in multi-metric batch mode. Call begin_multi_batch() first."
            return False

        self._batch_queue.append(MetricEntry(name=name, value=value, unit=unit, tags=tags))
        return True

    def send_batch(self) -> bool:
        """Send all queued metrics in a single batch request"""
        if not self._batch_mode or not self._batch_queue:
            return False

        try:
            metrics = []
            for entry in self._batch_queue:
                metric_data: Dict[str, Any] = {
                    "value": entry.value,
                    "unit": entry.unit,
                }
                if self._multi_batch_mode:
                    metric_data["name"] = entry.name
                formatted_tags = format_tags(entry.tags)
                if formatted_tags:
                    metric_data["tags"] = formatted_tags
                metrics.append(metric_data)

            payload: Dict[str, Any] = {
                "entity_id": self._entity_id,
                "metrics": metrics,
            }

            if not self._multi_batch_mode:
                payload["name"] = self._batch_metric_name

            url = f"{BASE_METRICS_URL}{ENDPOINT_BATCH}"
            response = self._http.post(url, payload)

            self._last_http_code = response.status

            if response.status in (200, 201):
                self._last_error = ""
                self.clear_batch()
                return True

            self._last_error = f"HTTP {response.status}"
            return False
        except Exception as e:
            self._last_error = str(e)
            return False

    def end_batch(self) -> None:
        """End batch mode and clear the queue"""
        self._batch_mode = False
        self._multi_batch_mode = False
        self.clear_batch()

    def clear_batch(self) -> None:
        """Clear the batch queue without sending"""
        self._batch_queue = []

    def get_batch_size(self) -> int:
        """Get the current batch queue size"""
        return len(self._batch_queue)

    def get_last_error(self) -> str:
        """Get the last error message"""
        return self._last_error

    def get_last_http_code(self) -> int:
        """Get the last HTTP response code"""
        return self._last_http_code

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable debug output"""
        self._debug_enabled = enabled


class LogDotMetrics:
    """
    LogDot Metrics client for entity management and metrics transmission.

    This is the main entry point for the metrics API. Use it to:
    1. Create or find entities
    2. Get a bound client with for_entity() to send metrics

    Example:
        metrics = LogDotMetrics(api_key='ilog_live_YOUR_API_KEY')

        # Create a new entity
        entity = metrics.create_entity(
            name='my-service',
            description='Production service',
        )

        # Or find an existing entity
        existing = metrics.get_entity_by_name('my-service')

        # Get a bound client for sending metrics
        client = metrics.for_entity(entity.id)
        client.send('response_time', 42, 'ms')
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 5000,
        retry_attempts: int = 3,
        retry_delay_ms: int = 1000,
        retry_max_delay_ms: int = 30000,
        debug: bool = False,
    ):
        """
        Create a new LogDot Metrics client.

        Args:
            api_key: API key for authentication (format: ilog_live_XXXXX)
            timeout: HTTP request timeout in milliseconds (default: 5000)
            retry_attempts: Maximum retry attempts for failed requests (default: 3)
            retry_delay_ms: Base delay in milliseconds for exponential backoff (default: 1000)
            retry_max_delay_ms: Maximum delay in milliseconds for exponential backoff (default: 30000)
            debug: Enable debug output to console (default: False)
        """
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
        self._debug_enabled = debug
        self._last_error = ""
        self._last_http_code = -1

    def create_entity(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Entity]:
        """
        Create a new entity.

        Args:
            name: Entity name
            description: Optional entity description
            metadata: Optional entity metadata

        Returns:
            The created Entity, or None if creation failed

        Example:
            entity = metrics.create_entity(
                name='my-service',
                description='My production service',
                metadata={'version': '1.0.0', 'region': 'us-east-1'}
            )
        """
        try:
            payload: Dict[str, Any] = {"name": name}

            if description:
                payload["description"] = description

            if metadata:
                payload["metadata"] = metadata

            url = f"{BASE_METRICS_URL}{ENDPOINT_ENTITIES}"
            response = self._http.post(url, payload)

            self._last_http_code = response.status

            if response.status in (200, 201) and response.data:
                data = response.data.get("data", {})
                entity_id = data.get("id")
                if entity_id:
                    self._last_error = ""
                    self._debug_log(f"Entity created: {entity_id}")
                    return Entity(id=entity_id, name=name, description=description)

            self._last_error = f"Failed to create entity. HTTP {response.status}"
            return None
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """
        Get an entity by name.

        Args:
            name: Entity name to look up

        Returns:
            The Entity if found, or None if not found

        Example:
            entity = metrics.get_entity_by_name('my-service')
            if entity:
                client = metrics.for_entity(entity.id)
                client.send('cpu', 50, 'percent')
        """
        try:
            url = f"{BASE_METRICS_URL}{ENDPOINT_ENTITIES_BY_NAME}/{quote(name)}"
            response = self._http.get(url)

            self._last_http_code = response.status

            if response.status == 200 and response.data:
                data = response.data.get("data", {})
                entity_id = data.get("id")
                if entity_id:
                    self._last_error = ""
                    self._debug_log(f"Entity found: {entity_id}")
                    return Entity(
                        id=entity_id,
                        name=data.get("name", name),
                        description=data.get("description"),
                    )

            self._last_error = f"Entity not found. HTTP {response.status}"
            return None
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_or_create_entity(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Entity]:
        """
        Get or create an entity by name.

        Args:
            name: Entity name
            description: Optional description (used if creating)
            metadata: Optional metadata (used if creating)

        Returns:
            The Entity (existing or newly created), or None on error

        Example:
            entity = metrics.get_or_create_entity(
                name='my-service',
                description='Created if not exists',
            )
        """
        # Try to find existing entity first
        existing = self.get_entity_by_name(name)
        if existing:
            return existing

        # Create new entity
        return self.create_entity(name, description, metadata)

    def for_entity(self, entity_id: str) -> BoundMetricsClient:
        """
        Create a bound metrics client for a specific entity.

        Args:
            entity_id: The entity ID to bind to

        Returns:
            A BoundMetricsClient for sending metrics to this entity

        Example:
            entity = metrics.create_entity(name='my-service')
            client = metrics.for_entity(entity.id)

            client.send('cpu.usage', 45, 'percent')
            client.send('memory.used', 1024, 'MB')
        """
        return BoundMetricsClient(self._http, entity_id, self._debug_enabled)

    def get_last_error(self) -> str:
        """Get the last error message"""
        return self._last_error

    def get_last_http_code(self) -> int:
        """Get the last HTTP response code"""
        return self._last_http_code

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable debug output"""
        self._debug_enabled = enabled

    def _debug_log(self, message: str) -> None:
        """Log debug message to console"""
        if self._debug_enabled:
            print(f"[LogDotMetrics] {message}")
