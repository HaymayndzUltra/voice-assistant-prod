# Configuration Management Guide

**Last Updated**: 2025-07-31  
**Version**: 3.4.0  
**Phase**: Phase 3.4 - Documentation & Developer Onboarding

## Table of Contents

1. [Overview](#overview)
2. [Configuration Architecture](#configuration-architecture)
3. [Environment Management](#environment-management)
4. [Schema Validation](#schema-validation)
5. [Agent Configuration](#agent-configuration)
6. [Backend Configuration](#backend-configuration)
7. [Monitoring Configuration](#monitoring-configuration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The AI System Monorepo uses a unified configuration management system that provides:

- **Environment-aware configurations** with dev/staging/prod overlays
- **JSON Schema validation** for configuration integrity
- **Type-safe access** with automatic conversion
- **Performance optimization** through caching
- **Legacy compatibility** with existing configuration patterns

## Configuration Architecture

### Directory Structure

```
common/config/
├── __init__.py                 # Package exports
├── unified_config_manager.py   # Core configuration manager
├── validation.py              # Schema validation system
├── defaults/                  # Default configurations
│   ├── base.yaml             # Base configuration
│   ├── dev.yaml              # Development overrides
│   ├── staging.yaml          # Staging overrides
│   └── prod.yaml             # Production overrides
└── schemas/                   # JSON Schema definitions
    ├── base.json             # Base schema
    ├── agent.json            # Agent-specific schema
    └── backend.json          # Backend configuration schema
```

### Configuration Loading Order

1. **Base Configuration**: Load `defaults/base.yaml`
2. **Environment Overlay**: Apply environment-specific overrides
3. **Environment Variables**: Override with environment variables
4. **Schema Validation**: Validate against JSON Schema
5. **Caching**: Cache validated configuration for performance

## Environment Management

### Environment Detection

The configuration system automatically detects the environment using:

1. `AI_SYSTEM_ENV` environment variable
2. `ENVIRONMENT` environment variable  
3. Defaults to `"dev"` if not specified

```bash
# Set environment
export AI_SYSTEM_ENV=prod

# Or use ENVIRONMENT
export ENVIRONMENT=staging
```

### Base Configuration (`base.yaml`)

```yaml
# System-wide configuration
system:
  name: "AI System Monorepo"
  version: "3.4.0" 
  environment: "dev"
  debug: true

# Logging configuration
logging:
  level: "INFO"
  file: "logs/system.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Network configuration
network:
  host: "0.0.0.0"
  port: 8080
  timeout: 30.0
  bind_address: "0.0.0.0"
  secure_zmq: false

# Performance settings
performance:
  max_workers: 4
  batch_size: 100
  cache_size: 1000
  queue_size: 10000

# Health monitoring
health:
  enabled: true
  interval: 30
  timeout: 5.0
  endpoint: "/health"

# Redis configuration
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: null
  ssl: false
  max_connections: 20

# ZMQ configuration
zmq:
  io_threads: 1
  max_sockets: 1024
  linger: 1000
  high_water_mark: 1000

# Model configuration
models:
  default_timeout: 30.0
  max_batch_size: 32
  cache_enabled: true

# Security settings
security:
  enable_auth: false
  ssl_enabled: false
  cert_file: null
  key_file: null

# Monitoring settings
monitoring:
  enabled: true
  port: 8000
  push_gateway: null
  collection_interval: 30

# Data processing
data:
  compression: true
  encoding: "utf-8"
  validation: true

# Agent defaults
agents:
  default_port: 8080
  health_check_interval: 30
  max_queue_size: 1000
  timeout: 30.0

# Port management
ports:
  auto_assign: true
  start_port: 8000
  health_port_offset: 1000
```

### Development Configuration (`dev.yaml`)

```yaml
# Development environment overrides
system:
  debug: true
  environment: "dev"

logging:
  level: "DEBUG"
  console_output: true

network:
  timeout: 60.0

performance:
  max_workers: 2
  batch_size: 10
  cache_size: 100

health:
  interval: 60  # Longer intervals in dev

redis:
  host: "localhost"

monitoring:
  enabled: true
  collection_interval: 60

security:
  enable_auth: false
  ssl_enabled: false

# Development-specific settings
development:
  auto_reload: true
  detailed_logging: true
  mock_external_services: true
  test_mode: false
```

### Staging Configuration (`staging.yaml`)

```yaml
# Staging environment overrides
system:
  debug: false
  environment: "staging"

logging:
  level: "INFO"
  console_output: false

performance:
  max_workers: 8
  batch_size: 50
  cache_size: 5000

health:
  interval: 30

redis:
  host: "staging-redis.internal"
  ssl: true

monitoring:
  enabled: true
  push_gateway: "http://prometheus-gateway.staging"
  collection_interval: 30

security:
  enable_auth: true
  ssl_enabled: true

# Staging-specific settings
staging:
  load_test_mode: true
  performance_profiling: true
  extended_monitoring: true
```

### Production Configuration (`prod.yaml`)

```yaml
# Production environment overrides
system:
  debug: false
  environment: "prod"

logging:
  level: "WARNING"
  console_output: false

network:
  secure_zmq: true

performance:
  max_workers: 16
  batch_size: 100
  cache_size: 10000

health:
  interval: 15

redis:
  host: "redis-cluster.prod.internal"
  ssl: true
  max_connections: 100

monitoring:
  enabled: true
  push_gateway: "http://prometheus-gateway.prod"
  collection_interval: 15

security:
  enable_auth: true
  ssl_enabled: true
  cert_file: "/etc/ssl/certs/ai-system.crt"
  key_file: "/etc/ssl/private/ai-system.key"

# Production-specific settings
production:
  high_availability: true
  auto_scaling: true
  disaster_recovery: true
  compliance_logging: true
```

## Schema Validation

### Base Schema (`schemas/base.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AI System Base Configuration",
  "type": "object",
  "properties": {
    "system": {
      "type": "object",
      "properties": {
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
        "environment": {"type": "string", "enum": ["dev", "staging", "prod"]},
        "debug": {"type": "boolean"}
      },
      "required": ["name", "environment"]
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        "file": {"type": "string"},
        "max_bytes": {"type": "integer", "minimum": 1024},
        "backup_count": {"type": "integer", "minimum": 1}
      },
      "required": ["level"]
    },
    "network": {
      "type": "object",
      "properties": {
        "host": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "timeout": {"type": "number", "minimum": 0.1}
      }
    },
    "performance": {
      "type": "object",
      "properties": {
        "max_workers": {"type": "integer", "minimum": 1},
        "batch_size": {"type": "integer", "minimum": 1},
        "cache_size": {"type": "integer", "minimum": 0}
      }
    }
  },
  "required": ["system", "logging"]
}
```

### Agent Schema (`schemas/agent.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AI System Agent Configuration",
  "allOf": [{"$ref": "base.json"}],
  "properties": {
    "agent": {
      "type": "object",
      "properties": {
        "name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
        "type": {"type": "string"},
        "enabled": {"type": "boolean"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "health_check": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "interval": {"type": "integer", "minimum": 1},
            "timeout": {"type": "number", "minimum": 0.1}
          }
        },
        "dependencies": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": ["name", "type"]
    }
  },
  "required": ["agent"]
}
```

### Custom Validators

The system includes custom validators for common configuration patterns:

```python
from common.config.validation import ConfigValidator

validator = ConfigValidator()

# Built-in validators
validators = {
    "port": "Validates port numbers (1-65535)",
    "ip_address": "Validates IP addresses and hostnames", 
    "url": "Validates HTTP/HTTPS URLs",
    "path": "Validates file paths",
    "agent_name": "Validates agent naming convention",
    "environment": "Validates environment names", 
    "log_level": "Validates logging levels",
    "timeout": "Validates timeout values",
    "redis_url": "Validates Redis connection URLs",
    "zmq_endpoint": "Validates ZMQ endpoint formats"
}
```

## Agent Configuration

### Loading Configuration in Agents

```python
from common.config import Config

class MyAgent(BaseAgent):
    def __init__(self, port: int = 8080):
        super().__init__(name="MyAgent", port=port)
        
        # Load agent-specific configuration
        self.config = Config.for_agent(__file__)
        
        # Access configuration values with type conversion
        self.timeout = self.config.float("network.timeout", 30.0)
        self.debug = self.config.bool("system.debug", False)
        self.workers = self.config.int("performance.max_workers", 4)
        self.redis_host = self.config.str("redis.host", "localhost")
```

### Configuration Access Patterns

```python
# String values
name = config.str("system.name")
host = config.str("network.host", "localhost")  # with default

# Numeric values  
port = config.int("network.port", 8080)
timeout = config.float("network.timeout", 30.0)

# Boolean values
debug = config.bool("system.debug", False)

# List values
dependencies = config.list("agent.dependencies", [])

# Dictionary values (nested)
redis_config = config.dict("redis", {})

# Raw access
raw_value = config.get("some.nested.key")
```

### Environment Variable Overrides

Configuration values can be overridden using environment variables:

```bash
# Override system name
export AI_SYSTEM_NAME="Production System"

# Override Redis host
export AI_REDIS_HOST="redis.prod.internal"

# Override logging level
export AI_LOGGING_LEVEL="ERROR"

# Boolean values
export AI_SYSTEM_DEBUG="false"
export AI_MONITORING_ENABLED="true"
```

The naming convention is: `AI_<SECTION>_<KEY>` where dots become underscores.

## Backend Configuration

### Memory Backend

```yaml
backends:
  memory:
    type: "memory"
    max_size: 10000
    eviction_policy: "lru"
```

### File Backend

```yaml
backends:
  file:
    type: "file"
    file_path: "data/backend.json"
    auto_save: true
    save_interval: 60
    backup_count: 5
```

### Redis Backend

```yaml
backends:
  redis:
    type: "redis"
    host: "localhost"
    port: 6379
    db: 0
    password: null
    ssl: false
    max_connections: 20
    connection_timeout: 5.0
    socket_timeout: 5.0
    
    # Clustering
    cluster_mode: false
    cluster_nodes: []
    
    # Sentinel
    sentinel_mode: false
    sentinel_hosts: []
    sentinel_service: "mymaster"
    
    # Performance
    key_prefix: "ai_system:"
    json_serializer: "orjson"  # or "ujson", "json"
```

### Backend Selection by Environment

```python
from common.backends import get_recommended_backend_type

# Automatic selection
backend_type = get_recommended_backend_type("prod")  # Returns "redis"
backend_type = get_recommended_backend_type("dev")   # Returns "memory"

# Manual configuration
backend_config = {
    "development": "memory",
    "testing": "memory",
    "staging": "redis", 
    "production": "redis"
}
```

## Monitoring Configuration

### Prometheus Configuration

```yaml
monitoring:
  prometheus:
    enabled: true
    namespace: "ai_system"
    port: 8000
    
    # HTTP server
    http_server: true
    
    # Push gateway
    push_gateway:
      enabled: false
      url: "http://prometheus-gateway:9091"
      job_name: "ai_system_job"
      interval: 30
    
    # Auto-collection
    auto_collection:
      enabled: true
      interval: 30
      
    # Custom metrics
    custom_metrics:
      - name: "business_events"
        type: "counter"
        help: "Business events counter"
        labels: ["event_type", "status"]
```

### Grafana Dashboard Configuration

```yaml
grafana:
  dashboards:
    - name: "AI System Overview"
      file: "common/monitoring/grafana_dashboards.json"
      datasource: "prometheus"
      
  alerts:
    - name: "High Error Rate"
      condition: "rate(ai_system_errors_total[5m]) > 0.1"
      severity: "warning"
      
    - name: "Queue Backlog"
      condition: "ai_system_queue_size > 1000"  
      severity: "critical"
```

## Best Practices

### 1. Configuration Organization

```python
# Good: Group related settings
database:
  host: "localhost"
  port: 5432
  pool_size: 10
  timeout: 30

# Avoid: Flat configuration
database_host: "localhost"
database_port: 5432
database_pool_size: 10
```

### 2. Use Type-Safe Access

```python
# Good: Use type conversion methods
port = config.int("network.port", 8080)
debug = config.bool("system.debug", False)

# Avoid: Manual conversion
port = int(config.get("network.port", "8080"))
debug = config.get("system.debug", "false").lower() == "true"
```

### 3. Provide Sensible Defaults

```python
# Good: Always provide defaults
timeout = config.float("network.timeout", 30.0)
workers = config.int("performance.max_workers", 4)

# Avoid: No defaults (may cause KeyError)
timeout = config.float("network.timeout")
```

### 4. Validate Early

```python
# Good: Validate configuration at startup
from common.config.validation import validate_agent_config

result = validate_agent_config(__file__)
if not result.valid:
    raise ConfigError(f"Invalid configuration: {result.errors}")

# Initialize agent only after validation
agent = MyAgent()
```

### 5. Environment-Specific Overrides

```yaml
# base.yaml - Conservative defaults
performance:
  max_workers: 4
  cache_size: 1000

# prod.yaml - Production optimizations  
performance:
  max_workers: 16
  cache_size: 10000
```

### 6. Sensitive Data Handling

```python
# Good: Use environment variables for secrets
redis_password = os.getenv("REDIS_PASSWORD")
api_key = os.getenv("API_KEY")

# Avoid: Hardcoding secrets in config files
redis:
  password: "secret123"  # Never do this!
```

### 7. Configuration Documentation

```python
class MyAgent(BaseAgent):
    """
    Agent for processing data.
    
    Configuration:
    - network.timeout (float): Request timeout in seconds (default: 30.0)
    - performance.batch_size (int): Batch processing size (default: 100)
    - redis.host (str): Redis server host (default: localhost)
    """
    def __init__(self):
        self.config = Config.for_agent(__file__)
        self.timeout = self.config.float("network.timeout", 30.0)
```

## Troubleshooting

### Common Issues

#### 1. Configuration Not Loading

**Problem**: Configuration values not being applied

**Solutions**:
```python
# Check environment detection
from common.config import Config
config = Config.for_agent(__file__)
print(f"Environment: {config.get('system.environment')}")

# Verify file existence
import os
config_path = "common/config/defaults/base.yaml"
print(f"Config exists: {os.path.exists(config_path)}")

# Check for YAML syntax errors
import yaml
with open(config_path) as f:
    yaml.safe_load(f)  # Will raise exception if invalid
```

#### 2. Schema Validation Failures

**Problem**: Configuration fails validation

**Solutions**:
```python
from common.config.validation import validate_agent_config

result = validate_agent_config(__file__)
print(f"Valid: {result.valid}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")

# Fix common validation issues:
# - Ensure required fields are present
# - Check data types match schema
# - Verify enum values are valid
```

#### 3. Environment Variables Not Working

**Problem**: Environment variable overrides not applied

**Solutions**:
```bash
# Check variable naming convention
export AI_SYSTEM_DEBUG="true"        # Correct
export SYSTEM_DEBUG="true"           # Incorrect

# Verify environment variables are set
env | grep AI_

# Check variable precedence
# Environment variables > config files > defaults
```

#### 4. Type Conversion Errors

**Problem**: Configuration values have wrong types

**Solutions**:
```python
# Use appropriate conversion methods
port = config.int("network.port", 8080)      # Convert to int
timeout = config.float("timeout", 30.0)      # Convert to float
debug = config.bool("debug", False)          # Convert to bool

# Handle conversion errors
try:
    port = config.int("network.port")
except (ValueError, TypeError) as e:
    logger.error(f"Invalid port configuration: {e}")
    port = 8080  # fallback
```

#### 5. Performance Issues

**Problem**: Configuration loading is slow

**Solutions**:
```python
# Configuration is cached by default, but you can verify:
from common.config import Config

# First load (slow)
config1 = Config.for_agent(__file__)

# Subsequent loads (fast, cached)
config2 = Config.for_agent(__file__)

# Clear cache if needed (for testing)
Config._cache.clear()
```

### Debugging Configuration

```python
# Enable debug logging for configuration
import logging
logging.getLogger("config").setLevel(logging.DEBUG)

# Print current configuration
config = Config.for_agent(__file__)
print("Current configuration:")
for key, value in config._config_data.items():
    print(f"  {key}: {value}")

# Validate configuration
from common.config.validation import ConfigValidator
validator = ConfigValidator()
result = validator.validate_config(config._config_data)
print(f"Validation result: {result}")
```

### Configuration Testing

```python
import pytest
from common.config import Config

def test_agent_configuration():
    """Test agent configuration loading."""
    config = Config.for_agent(__file__)
    
    # Test required values
    assert config.str("system.name") is not None
    assert config.str("system.environment") in ["dev", "staging", "prod"]
    
    # Test type conversions
    assert isinstance(config.int("network.port"), int)
    assert isinstance(config.bool("system.debug"), bool)
    
    # Test defaults
    assert config.float("network.timeout", 30.0) >= 0.1

def test_environment_overrides():
    """Test environment variable overrides."""
    import os
    
    # Set environment variable
    os.environ["AI_SYSTEM_DEBUG"] = "true"
    
    config = Config.for_agent(__file__)
    assert config.bool("system.debug") is True
    
    # Cleanup
    del os.environ["AI_SYSTEM_DEBUG"]
```

---

**Next**: See [error_handling.md](error_handling.md) for comprehensive error management patterns and [architecture.md](architecture.md) for system architecture overview.
