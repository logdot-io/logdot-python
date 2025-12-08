"""
LogDot SDK Type Definitions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(str, Enum):
    """Log severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class BaseConfig:
    """Base configuration options shared by all clients"""
    api_key: str
    timeout: int = 5000  # milliseconds
    retry_attempts: int = 3
    retry_delay_ms: int = 1000
    retry_max_delay_ms: int = 30000
    debug: bool = False


@dataclass
class LoggerConfig(BaseConfig):
    """Configuration options for LogDot Logger"""
    hostname: str = "unknown"


@dataclass
class MetricsConfig(BaseConfig):
    """Configuration options for LogDot Metrics"""
    # No entity-specific config - use for_entity() after creating/finding entity
    pass


@dataclass
class LogDotConfig(BaseConfig):
    """
    Deprecated: Use LoggerConfig or MetricsConfig instead.
    """
    hostname: Optional[str] = None
    entity_name: Optional[str] = None
    entity_description: Optional[str] = None


@dataclass
class LogEntry:
    """A single log entry"""
    message: str
    level: LogLevel
    tags: Optional[Dict[str, Any]] = None


@dataclass
class MetricEntry:
    """A single metric entry"""
    name: str
    value: float
    unit: str
    tags: Optional[Dict[str, Any]] = None


@dataclass
class Entity:
    """Entity information returned from create/get operations"""
    id: str
    name: str
    description: Optional[str] = None


@dataclass
class CreateEntityOptions:
    """Options for creating an entity"""
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000


@dataclass
class HttpResponse:
    """HTTP response wrapper"""
    status: int
    data: Optional[Dict[str, Any]] = None
