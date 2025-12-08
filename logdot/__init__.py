"""
LogDot SDK for Python - Cloud logging and metrics made simple.

Example usage:
    from logdot import LogDotLogger, LogDotMetrics

    # === LOGGING ===
    logger = LogDotLogger(
        api_key='ilog_live_YOUR_API_KEY',
        hostname='my-service',
    )

    logger.info('Application started')
    logger.error('Something went wrong', {'error_code': 500})

    # Context-aware logging
    user_logger = logger.with_context({'user_id': 123})
    user_logger.info('User action')  # Includes user_id automatically

    # === METRICS ===
    metrics = LogDotMetrics(api_key='ilog_live_YOUR_API_KEY')

    # Create or find an entity
    entity = metrics.get_or_create_entity(
        name='my-service',
        description='My production service',
    )

    # Bind to the entity and send metrics
    metrics_client = metrics.for_entity(entity.id)
    metrics_client.send('cpu.usage', 45.5, 'percent')
    metrics_client.send('response_time', 42, 'ms', {'endpoint': '/api/users'})
"""

from logdot.logger import LogDotLogger
from logdot.metrics import LogDotMetrics, BoundMetricsClient
from logdot.types import (
    LogLevel,
    LoggerConfig,
    MetricsConfig,
    LogEntry,
    MetricEntry,
    Entity,
    CreateEntityOptions,
    # Deprecated
    LogDotConfig,
)

__version__ = "1.0.0"
__all__ = [
    # Main classes
    "LogDotLogger",
    "LogDotMetrics",
    "BoundMetricsClient",
    # Types
    "LogLevel",
    "LoggerConfig",
    "MetricsConfig",
    "LogEntry",
    "MetricEntry",
    "Entity",
    "CreateEntityOptions",
    # Deprecated
    "LogDotConfig",
]
