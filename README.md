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

## Auto-Instrumentation (Django)

Automatically log all HTTP requests, errors, and response time metrics in Django apps with zero manual logging code.

### Setup

Add to your `settings.py`:

```python
# Required
LOGDOT_API_KEY = 'ilog_live_YOUR_API_KEY'
LOGDOT_HOSTNAME = 'my-django-app'

MIDDLEWARE = [
    'logdot.django.LogdotMiddleware',
    # ... your other middleware
]
```

### What Gets Captured

- **HTTP requests** — Every request logged with method, path, status code, and duration
- **Errors** — Unhandled exceptions with full traceback and request context
- **Metrics** — Response time per endpoint (entity is automatically created/resolved on first request using `LOGDOT_ENTITY_NAME`)

### Configuration

| Setting | Type | Required | Default | Description |
|---------|------|----------|---------|-------------|
| `LOGDOT_API_KEY` | str | Yes | — | Your LogDot API key |
| `LOGDOT_HOSTNAME` | str | Yes | — | Identifies this service in logs |
| `LOGDOT_ENTITY_NAME` | str | No | hostname | Metrics entity name — automatically created if it doesn't exist |
| `LOGDOT_DEBUG` | bool | No | `False` | Enable debug output |
| `LOGDOT_TIMEOUT` | int | No | `5000` | HTTP timeout in ms |
| `LOGDOT_LOG_REQUESTS` | bool | No | `True` | Enable request logging |
| `LOGDOT_LOG_METRICS` | bool | No | `True` | Enable duration metrics |
| `LOGDOT_IGNORE_PATHS` | list | No | `[]` | Paths to skip (e.g. `["/health"]`) |
| `LOGDOT_CAPTURE_LOGGING` | bool | No | `False` | Forward Python `logging` and `print()` to LogDot |

## Log Capture

Automatically forward Python `logging` calls and `print()` output to LogDot. The original behavior is preserved — logs still appear in your console and log files as usual.

This works in **any Python application** (Flask, FastAPI, scripts, CLI tools, Celery workers, etc.), not just Django.

### Capturing `logging` Output

Forward all stdlib `logging` records to LogDot:

```python
import logging
from logdot import LogDotLogger, LogdotLoggingHandler

logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',
)

# Attach to the root logger
handler = LogdotLoggingHandler(logger=logger)
logging.root.addHandler(handler)
logging.root.setLevel(logging.DEBUG)

# All logging calls are now sent to LogDot
logging.info('This goes to LogDot')
logging.error('Error occurred', exc_info=True)
```

Log records are mapped to LogDot severity levels:

| Python Level | LogDot Severity |
|-------------|----------------|
| `DEBUG` | `debug` |
| `INFO` | `info` |
| `WARNING` | `warn` |
| `ERROR` | `error` |
| `CRITICAL` | `error` |

Each captured log includes tags with the logger name, file path, line number, and function name. If the record has exception info, the exception type and message are also included.

### Capturing `print()` Output

Forward `print()` calls (stdout and stderr) to LogDot:

```python
from logdot import LogDotLogger, enable_print_capture, disable_print_capture

logger = LogDotLogger(
    api_key='ilog_live_YOUR_API_KEY',
    hostname='my-service',
)

enable_print_capture(logger=logger)

# print() calls are now sent to LogDot
print('This goes to LogDot')            # severity: info (stdout)
print('Error!', file=sys.stderr)        # severity: error (stderr)

# Stop capturing
disable_print_capture()
```

### With Django

When using the Django auto-instrumentation, set `LOGDOT_CAPTURE_LOGGING = True` in `settings.py` to enable both `logging` and `print()` capture automatically:

```python
# settings.py
LOGDOT_API_KEY = 'ilog_live_YOUR_API_KEY'
LOGDOT_HOSTNAME = 'my-django-app'
LOGDOT_CAPTURE_LOGGING = True

MIDDLEWARE = [
    'logdot.django.LogdotMiddleware',
    # ...
]
```

### How It Works

**`LogdotLoggingHandler`** is a standard `logging.Handler` subclass:

1. Receives `LogRecord` objects from the stdlib logging system
2. Formats the message and maps the log level to a LogDot severity
3. Extracts metadata (logger name, file, line, exception info) into tags
4. Calls the underlying `LogDotLogger` to send to LogDot
5. A **thread-local recursion guard** prevents infinite loops — when LogDot's HTTP client triggers urllib3/requests logging during delivery, those records are silently skipped
6. Messages longer than 16KB are truncated

**`enable_print_capture`** wraps `sys.stdout` and `sys.stderr`:

1. Replaces `sys.stdout` and `sys.stderr` with wrapper objects
2. Each `write()` call forwards to the original stream **and** sends to LogDot
3. `stdout` writes are sent with severity `info`, `stderr` with severity `error`
4. Empty/whitespace-only writes are skipped
5. Same thread-local recursion guard applies
6. Call `disable_print_capture()` to restore the original streams

### Tags

| Source | Tag | Value |
|--------|-----|-------|
| `logging` | `source` | `"python_logging"` |
| `logging` | `logger_name` | Logger name (e.g. `"myapp.views"`) |
| `logging` | `pathname` | File path |
| `logging` | `lineno` | Line number |
| `logging` | `func_name` | Function name |
| `logging` | `exception_type` | Exception class name (if present) |
| `logging` | `exception_message` | Exception message (if present) |
| `print()` | `source` | `"print"` |

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

### LogdotLoggingHandler

| Method | Description |
|--------|-------------|
| `LogdotLoggingHandler(logger)` | Create handler bound to a `LogDotLogger` instance |
| `emit(record)` | Forward a `logging.LogRecord` to LogDot (called automatically) |

### Log Capture Functions

| Function | Description |
|----------|-------------|
| `enable_print_capture(logger)` | Start forwarding `print()` output to LogDot |
| `disable_print_capture()` | Restore original `sys.stdout` and `sys.stderr` |

## Requirements

- Python 3.8+
- requests >= 2.25.0

## Examples

Create a `.env` file in the repo root with your API key:

```
LOGDOT_API_KEY=ilog_live_YOUR_API_KEY
```

### Core SDK test app

Tests logging, metrics, context, and batch operations:

```bash
cd python
python examples/test_app.py
```

### Django hooks test app

Tests Django middleware, logging capture, and print capture:

```bash
cd python
pip install django    # if not already installed
python examples/test_django_app.py
```

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <a href="https://logdot.io">logdot.io</a> •
  Built with care for developers
</p>
