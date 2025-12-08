# LogDot SDK for Python

Official Python SDK for [LogDot](https://logdot.io) - Cloud logging and metrics made simple.

## Features

- **Separate Clients**: Independent logger and metrics clients for flexibility
- **Context-Aware Logging**: Create loggers with persistent context that's automatically added to all logs
- **Type Hints**: Full type annotation support for better IDE integration
- **Flexible Logging**: 4 log levels (debug, info, warn, error) with structured tags
- **Entity-Based Metrics**: Create/find entities, then bind to them for sending metrics
- **Batch Operations**: Efficiently send multiple logs or metrics in a single request
- **Automatic Retry**: Exponential backoff retry with configurable attempts
- **Python 3.8+**: Compatible with Python 3.8 and newer

## Installation

```bash
pip install logdot
```

## Quick Start

```python
from logdot import LogDotLogger, LogDotMetrics

# === LOGGING ===
logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',
)

logger.info('Application started')
logger.error('Something went wrong', {'error_code': 500})

# === METRICS ===
metrics = LogDotMetrics(
    api_key='ilog_live_YOUR_API_KEY',
)

# Create or find an entity first
entity = metrics.get_or_create_entity(
    name='my-service',
    description='My production service',
)

# Bind to the entity for sending metrics
metrics_client = metrics.for_entity(entity.id)
metrics_client.send('response_time', 123.45, 'ms')
```

## Logging

### Configuration

```python
from logdot import LogDotLogger

logger = LogDotLogger(
    # Required
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',

    # Optional - defaults shown
    timeout=5000,                 # HTTP timeout (ms)
    retry_attempts=3,             # Max retry attempts
    retry_delay_ms=1000,          # Base retry delay (ms)
    retry_max_delay_ms=30000,     # Max retry delay (ms)
    debug=False,                  # Enable debug output
)
```

### Basic Logging

```python
logger.debug('Debug message')
logger.info('Info message')
logger.warn('Warning message')
logger.error('Error message')
```

### Logging with Tags

```python
logger.info('User logged in', {
    'user_id': 12345,
    'ip_address': '192.168.1.1',
    'browser': 'Chrome',
})

logger.error('Database connection failed', {
    'host': 'db.example.com',
    'port': 5432,
    'error': 'Connection timeout',
})
```

### Context-Aware Logging

Create loggers with persistent context that's automatically added to all logs:

```python
from logdot import LogDotLogger

logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',
)

# Create a logger with context for a specific request
request_logger = logger.with_context({
    'request_id': 'abc-123',
    'user_id': 456,
})

# All logs from request_logger will include request_id and user_id
request_logger.info('Processing request')
request_logger.debug('Fetching user data')
request_logger.info('Request completed')

# You can chain contexts - they merge together
detailed_logger = request_logger.with_context({
    'operation': 'checkout',
})

# This log will have request_id, user_id, AND operation
detailed_logger.info('Starting checkout process')

# Original logger is unchanged
logger.info('This log has no context')
```

### Context with Additional Tags

When you provide tags to a log call, they're merged with the context (tags take precedence):

```python
logger = LogDotLogger(
    api_key='...',
    hostname='api',
).with_context({
    'service': 'api',
    'environment': 'production',
})

# The log will have: service, environment, endpoint, status
logger.info('Request handled', {
    'endpoint': '/users',
    'status': 200,
})

# Override context values if needed
logger.info('Custom service', {
    'service': 'worker',  # This overrides the context value
})
```

### Batch Logging

Send multiple logs in a single HTTP request for better efficiency:

```python
# Start batch mode
logger.begin_batch()

# Queue logs (no network calls yet)
logger.info('Request received')
logger.debug('Processing started')
logger.info('Processing complete')

# Send all logs in one request
logger.send_batch()

# End batch mode
logger.end_batch()
```

## Metrics

### Configuration

```python
from logdot import LogDotMetrics

metrics = LogDotMetrics(
    # Required
    api_key='ilog_live_YOUR_API_KEY',

    # Optional - defaults shown
    timeout=5000,                 # HTTP timeout (ms)
    retry_attempts=3,             # Max retry attempts
    retry_delay_ms=1000,          # Base retry delay (ms)
    retry_max_delay_ms=30000,     # Max retry delay (ms)
    debug=False,                  # Enable debug output
)
```

### Entity Management

Before sending metrics, you need to create or find an entity:

```python
# Create a new entity
entity = metrics.create_entity(
    name='my-service',
    description='My production service',
    metadata={
        'environment': 'production',
        'region': 'us-east-1',
        'version': '1.2.3',
    },
)

# Or find an existing entity by name
existing = metrics.get_entity_by_name('my-service')

# Or get or create (finds existing, creates if not found)
entity = metrics.get_or_create_entity(
    name='my-service',
    description='Created if not exists',
)
```

### Binding to an Entity

Once you have an entity, bind to it for sending metrics:

```python
entity = metrics.get_or_create_entity(name='my-service')
metrics_client = metrics.for_entity(entity.id)

# Now send metrics
metrics_client.send('cpu_usage', 45.2, 'percent')
metrics_client.send('response_time', 123.45, 'ms', {
    'endpoint': '/api/users',
    'method': 'GET',
})
```

### Batch Metrics (Same Metric)

Send multiple values for the same metric:

```python
# Start batch for a specific metric
metrics_client.begin_batch('temperature', 'celsius')

# Add values
metrics_client.add(23.5)
metrics_client.add(24.1)
metrics_client.add(23.8)
metrics_client.add(24.5)

# Send all values in one request
metrics_client.send_batch()

# End batch mode
metrics_client.end_batch()
```

### Multi-Metric Batch

Send different metrics in a single request:

```python
# Start multi-metric batch
metrics_client.begin_multi_batch()

# Add different metrics
metrics_client.add_metric('cpu_usage', 45.2, 'percent')
metrics_client.add_metric('memory_used', 2048, 'MB')
metrics_client.add_metric('disk_free', 50.5, 'GB')

# Send all metrics in one request
metrics_client.send_batch()

# End batch mode
metrics_client.end_batch()
```

## Error Handling

```python
# Check if operations succeeded
if not logger.info('Test message'):
    print('Failed to send log')

# For metrics, check last error
if not metrics_client.send('test', 1, 'unit'):
    print('Failed to send metric:', metrics_client.get_last_error())
    print('HTTP code:', metrics_client.get_last_http_code())
```

## Debug Mode

Enable debug output to see HTTP requests and responses:

```python
logger = LogDotLogger(
    api_key='...',
    hostname='my-service',
    debug=True,  # Enable at construction
)

# Or enable later
logger.set_debug(True)
```

## API Reference

### LogDotLogger

| Method | Description |
|--------|-------------|
| `with_context(context)` | Create new logger with merged context |
| `get_context()` | Get current context dict |
| `debug(message, tags=None)` | Send debug log |
| `info(message, tags=None)` | Send info log |
| `warn(message, tags=None)` | Send warning log |
| `error(message, tags=None)` | Send error log |
| `log(level, message, tags=None)` | Send log at specified level |
| `begin_batch()` | Start batch mode |
| `send_batch()` | Send queued logs |
| `end_batch()` | End batch mode |
| `clear_batch()` | Clear queue without sending |
| `get_batch_size()` | Get queue size |
| `get_hostname()` | Get hostname |
| `set_debug(enabled)` | Enable/disable debug |

### LogDotMetrics

| Method | Description |
|--------|-------------|
| `create_entity(name, description, metadata)` | Create a new entity |
| `get_entity_by_name(name)` | Find entity by name |
| `get_or_create_entity(name, description, metadata)` | Get existing or create new entity |
| `for_entity(entity_id)` | Create bound client for entity |
| `get_last_error()` | Get last error message |
| `get_last_http_code()` | Get last HTTP code |
| `set_debug(enabled)` | Enable/disable debug |

### BoundMetricsClient (from `for_entity`)

| Method | Description |
|--------|-------------|
| `get_entity_id()` | Get bound entity ID |
| `send(name, value, unit, tags=None)` | Send single metric |
| `begin_batch(name, unit)` | Start single-metric batch |
| `add(value, tags=None)` | Add to single-metric batch |
| `begin_multi_batch()` | Start multi-metric batch |
| `add_metric(name, value, unit, tags=None)` | Add to multi-metric batch |
| `send_batch()` | Send queued metrics |
| `end_batch()` | End batch mode |
| `clear_batch()` | Clear queue |
| `get_batch_size()` | Get queue size |
| `get_last_error()` | Get last error message |
| `get_last_http_code()` | Get last HTTP code |
| `set_debug(enabled)` | Enable/disable debug |

## Requirements

- Python 3.8 or higher
- requests >= 2.25.0

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [LogDot Website](https://logdot.io)
- [Documentation](https://docs.logdot.io/python)
- [GitHub Repository](https://github.com/logdot/logdot-python)
