<p align="center">
  <h1 align="center">LogDot SDK for Python</h1>
  <p align="center">
    <strong>Cloud logging and metrics made simple</strong>
  </p>
</p>

<p align="center">
  <a href="https://pypi.org/project/logdot-io-sdk/"><img src="https://img.shields.io/pypi/v/logdot-io-sdk?style=flat-square&color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/logdot-io-sdk/"><img src="https://img.shields.io/pypi/dm/logdot-io-sdk?style=flat-square" alt="PyPI downloads"></a>
  <a href="https://github.com/logdot-io/logdot-python/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-%3E%3D3.8-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://github.com/python/mypy"><img src="https://img.shields.io/badge/type_hints-ready-blue?style=flat-square" alt="Type Hints"></a>
</p>

<p align="center">
  <a href="https://logdot.io">Website</a> •
  <a href="https://docs.logdot.io">Documentation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#api-reference">API Reference</a>
</p>

---

## Features

- **Separate Clients** — Independent logger and metrics clients for maximum flexibility
- **Context-Aware Logging** — Create loggers with persistent context that automatically flows through your application
- **Type Hints** — Full type annotation support for better IDE integration
- **Entity-Based Metrics** — Create/find entities, then bind to them for organized metric collection
- **Batch Operations** — Efficiently send multiple logs or metrics in a single request
- **Automatic Retry** — Exponential backoff retry with configurable attempts

## Installation

```bash
pip install logdot-io-sdk
```

## Quick Start

```python
from logdot import LogDotLogger, LogDotMetrics

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',
)

logger.info('Application started')
logger.error('Something went wrong', {'error_code': 500})

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',  # Required
    hostname='my-service',              # Required

    # Optional settings
    timeout=5000,            # HTTP timeout (ms)
    retry_attempts=3,        # Max retry attempts
    retry_delay_ms=1000,     # Base retry delay (ms)
    retry_max_delay_ms=30000,  # Max retry delay (ms)
    debug=False,             # Enable debug output
)
```

### Log Levels

```python
logger.debug('Debug message')
logger.info('Info message')
logger.warn('Warning message')
logger.error('Error message')
```

### Structured Tags

```python
logger.info('User logged in', {
    'user_id': 12345,
    'ip_address': '192.168.1.1',
    'browser': 'Chrome',
})
```

### Context-Aware Logging

Create loggers with persistent context that automatically flows through your application:

```python
# Create a logger with context for a specific request
request_logger = logger.with_context({
    'request_id': 'abc-123',
    'user_id': 456,
})

# All logs include request_id and user_id automatically
request_logger.info('Processing request')
request_logger.debug('Fetching user data')

# Chain contexts — they merge together
detailed_logger = request_logger.with_context({
    'operation': 'checkout',
})

# This log has request_id, user_id, AND operation
detailed_logger.info('Starting checkout process')
```

### Batch Logging

Send multiple logs in a single HTTP request:

```python
logger.begin_batch()

logger.info('Step 1 complete')
logger.info('Step 2 complete')
logger.info('Step 3 complete')

logger.send_batch()  # Single HTTP request
logger.end_batch()
```

## Metrics

### Entity Management

```python
metrics = LogDotMetrics(api_key='...')

# Create a new entity
entity = metrics.create_entity(
    name='my-service',
    description='Production API server',
    metadata={'environment': 'production', 'region': 'us-east-1'},
)

# Find existing entity
existing = metrics.get_entity_by_name('my-service')

# Get or create (recommended)
entity = metrics.get_or_create_entity(
    name='my-service',
    description='Created if not exists',
)
```

### Sending Metrics

```python
metrics_client = metrics.for_entity(entity.id)

# Single metric
metrics_client.send('cpu_usage', 45.2, 'percent')
metrics_client.send('response_time', 123.45, 'ms', {
    'endpoint': '/api/users',
    'method': 'GET',
})
```

### Batch Metrics

```python
# Same metric, multiple values
metrics_client.begin_batch('temperature', 'celsius')
metrics_client.add(23.5)
metrics_client.add(24.1)
metrics_client.add(23.8)
metrics_client.send_batch()
metrics_client.end_batch()

# Multiple different metrics
metrics_client.begin_multi_batch()
metrics_client.add_metric('cpu_usage', 45.2, 'percent')
metrics_client.add_metric('memory_used', 2048, 'MB')
metrics_client.add_metric('disk_free', 50.5, 'GB')
metrics_client.send_batch()
metrics_client.end_batch()
```

## API Reference

### LogDotLogger

| Method | Description |
|--------|-------------|
| `with_context(context)` | Create new logger with merged context |
| `get_context()` | Get current context dict |
| `debug/info/warn/error(message, tags=None)` | Send log at level |
| `begin_batch()` | Start batch mode |
| `send_batch()` | Send queued logs |
| `end_batch()` | End batch mode |
| `clear_batch()` | Clear queue without sending |
| `get_batch_size()` | Get queue size |

### LogDotMetrics

| Method | Description |
|--------|-------------|
| `create_entity(name, description, metadata)` | Create a new entity |
| `get_entity_by_name(name)` | Find entity by name |
| `get_or_create_entity(name, description, metadata)` | Get existing or create new |
| `for_entity(entity_id)` | Create bound metrics client |

### BoundMetricsClient

| Method | Description |
|--------|-------------|
| `send(name, value, unit, tags=None)` | Send single metric |
| `begin_batch(name, unit)` | Start single-metric batch |
| `add(value, tags=None)` | Add to batch |
| `begin_multi_batch()` | Start multi-metric batch |
| `add_metric(name, value, unit, tags=None)` | Add metric to batch |
| `send_batch()` | Send queued metrics |
| `end_batch()` | End batch mode |

## Requirements

- Python 3.8+
- requests >= 2.25.0

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <a href="https://logdot.io">logdot.io</a> •
  Built with care for developers
</p>
