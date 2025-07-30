# Error Handling Guide

**Last Updated**: 2025-07-31  
**Version**: 3.4.0  
**Phase**: Phase 3.4 - Documentation & Developer Onboarding

## Table of Contents

1. [Overview](#overview)
2. [Error Bus Architecture](#error-bus-architecture)
3. [Error Types and Categories](#error-types-and-categories)
4. [Implementation Patterns](#implementation-patterns)
5. [Cross-Machine Error Propagation](#cross-machine-error-propagation)
6. [Error Monitoring and Alerting](#error-monitoring-and-alerting)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The AI System Monorepo implements a comprehensive error handling system that provides:

- **Centralized error collection** across all agents and components
- **Real-time error monitoring** with metrics and alerting
- **Cross-machine error propagation** between Main PC and PC2
- **Categorized error reporting** for efficient triage
- **Performance impact assessment** for critical errors
- **Self-healing capabilities** through error pattern recognition

## Error Bus Architecture

### Core Components

```
Error Handling System
├── Main PC Error Bus
│   ├── error_publisher.py        # Main error collection and publishing
│   ├── error_subscriber.py       # Error consumption and processing
│   └── error_aggregator.py       # Error aggregation and analytics
├── PC2 Error Bus
│   ├── pc2_error_publisher.py    # PC2-specific error handling
│   └── cross_machine_bridge.py   # PC2 → Main PC propagation
├── Error Storage
│   ├── redis_error_store.py      # Redis-backed error storage
│   └── file_error_store.py       # File-based error logging
└── Monitoring
    ├── prometheus_error_metrics.py # Error metrics for Prometheus
    └── grafana_error_dashboards/   # Error visualization dashboards
```

### Error Flow Architecture

```
[Agent] → [Error Publisher] → [Error Bus] → [Error Storage]
                                    ↓
                              [Error Analytics] → [Alerting]
                                    ↓
                              [Self-Healing] → [Recovery Actions]
```

## Error Types and Categories

### Error Severity Levels

```python
class ErrorSeverity(Enum):
    CRITICAL = "critical"    # System-threatening errors requiring immediate attention
    HIGH = "high"           # Significant errors affecting functionality
    MEDIUM = "medium"       # Moderate errors with workarounds available
    LOW = "low"            # Minor errors or warnings
    INFO = "info"          # Informational messages
```

### Error Categories

```python
# System Errors
SYSTEM_ERRORS = {
    "network": ["connection_timeout", "socket_error", "dns_resolution"],
    "memory": ["out_of_memory", "memory_leak", "allocation_failure"],
    "disk": ["disk_full", "io_error", "permission_denied"],
    "cpu": ["high_cpu_usage", "process_timeout", "resource_exhaustion"]
}

# Application Errors
APPLICATION_ERRORS = {
    "agent": ["initialization_failure", "communication_error", "state_corruption"],
    "data": ["validation_error", "parsing_error", "transformation_error"],
    "external": ["api_error", "service_unavailable", "authentication_failure"]
}

# PC2-Specific Errors
PC2_ERRORS = {
    "pc2_memory": ["memory_orchestrator_failure", "cache_manager_error"],
    "pc2_vision": ["vision_processing_error", "image_analysis_failure"],
    "pc2_reasoning": ["reasoning_engine_error", "context_analysis_failure"],
    "pc2_communication": ["cross_machine_communication_error", "network_bridge_failure"]
}
```

## Implementation Patterns

### Basic Error Reporting

```python
from common.error_handling import ErrorPublisher

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.error_publisher = ErrorPublisher()
    
    def process_data(self, data):
        try:
            result = self.transform_data(data)
            return result
        except ValidationError as e:
            self.error_publisher.report_error(
                error_type="data_validation",
                severity="medium",
                message=f"Data validation failed: {str(e)}",
                context={
                    "agent_name": self.name,
                    "data_type": type(data).__name__,
                    "validation_rule": e.rule_name
                },
                performance_impact="low"
            )
            raise
        except Exception as e:
            self.error_publisher.report_error(
                error_type="processing_error",
                severity="high",
                message=f"Unexpected error during processing: {str(e)}",
                context={
                    "agent_name": self.name,
                    "error_class": type(e).__name__,
                    "stack_trace": traceback.format_exc()
                },
                performance_impact="medium"
            )
            raise
```

### PC2 Error Reporting

```python
from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher

class PC2Agent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.error_publisher = PC2ErrorPublisher()
    
    def execute_pc2_task(self, task):
        try:
            result = self.process_task(task)
            return result
        except MemoryError as e:
            self.error_publisher.report_error(
                error_type="pc2_memory_error",
                severity="critical",
                message=f"Memory error in PC2 task: {str(e)}",
                context={
                    "pc2_component": "memory_orchestrator",
                    "task_type": task.type,
                    "memory_usage": self.get_memory_usage()
                },
                performance_impact="critical",
                cross_machine_propagate=True  # Send to Main PC
            )
            raise
```

### Async Error Handling

```python
import asyncio
from common.error_handling import AsyncErrorPublisher

class AsyncAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.error_publisher = AsyncErrorPublisher()
    
    async def async_process(self, data):
        try:
            result = await self.async_transform(data)
            return result
        except asyncio.TimeoutError as e:
            await self.error_publisher.report_error_async(
                error_type="async_timeout",
                severity="high",
                message=f"Async operation timed out: {str(e)}",
                context={
                    "agent_name": self.name,
                    "operation": "async_transform",
                    "timeout_duration": self.timeout
                },
                performance_impact="high"
            )
            raise
```

## Cross-Machine Error Propagation

### PC2 to Main PC Propagation

```python
class PC2ErrorPublisher(ErrorPublisher):
    def __init__(self):
        super().__init__()
        self.main_pc_endpoint = "tcp://main-pc:5555"
        self.setup_cross_machine_communication()
    
    def report_error(self, error_type, severity, message, context=None, 
                    performance_impact="none", cross_machine_propagate=False):
        
        # Standard local error reporting
        super().report_error(error_type, severity, message, context, performance_impact)
        
        # Cross-machine propagation for critical/high severity errors
        if cross_machine_propagate or severity in ["critical", "high"]:
            self.propagate_to_main_pc(error_type, severity, message, context, performance_impact)
    
    def propagate_to_main_pc(self, error_type, severity, message, context, performance_impact):
        cross_machine_error = {
            "source_machine": "PC2",
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "severity": severity,
            "message": message,
            "context": context or {},
            "performance_impact": performance_impact,
            "pc2_component": context.get("pc2_component", "unknown") if context else "unknown"
        }
        
        try:
            self.cross_machine_socket.send_json(cross_machine_error, zmq.NOBLOCK)
        except Exception as e:
            logger.error(f"Cross-machine error propagation failed: {e}")
```

## Error Monitoring and Alerting

### Prometheus Error Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Error metrics
error_counter = Counter(
    'ai_system_errors_total',
    'Total number of errors',
    ['error_type', 'severity', 'component', 'machine']
)

error_duration = Histogram(
    'ai_system_error_processing_duration_seconds',
    'Time spent processing errors',
    ['error_type', 'severity']
)

active_errors = Gauge(
    'ai_system_active_errors',
    'Number of active unresolved errors',
    ['error_type', 'severity']
)
```

### Alerting Rules

```yaml
# Prometheus Alerting Rules
groups:
- name: ai_system_errors
  rules:
  - alert: HighErrorRate
    expr: rate(ai_system_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"
  
  - alert: CriticalErrorSpike
    expr: increase(ai_system_errors_total{severity="critical"}[1m]) > 5
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "Critical error spike detected"
      description: "{{ $value }} critical errors in the last minute"
  
  - alert: PC2CommunicationFailure
    expr: ai_system_errors_total{error_type="cross_machine_communication_error"} > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "PC2 communication failure"
      description: "Communication between PC2 and Main PC has failed"
```

## Best Practices

### 1. Error Message Quality

```python
# Good: Descriptive, actionable error messages
self.error_publisher.report_error(
    error_type="database_connection_error",
    severity="high",
    message="Failed to connect to PostgreSQL database 'ai_system' on host 'db.internal:5432'. "
            "Connection timeout after 30 seconds. Check network connectivity and database status.",
    context={
        "database_host": "db.internal",
        "database_port": 5432,
        "database_name": "ai_system",
        "timeout_duration": 30,
        "connection_attempts": 3
    }
)

# Avoid: Vague, unhelpful error messages
self.error_publisher.report_error(
    error_type="error",
    severity="high", 
    message="Something went wrong",
    context={}
)
```

### 2. Appropriate Error Severity

```python
# Critical: System-threatening errors
severity="critical" → "Database cluster is down, system cannot function"
severity="critical" → "Memory corruption detected, agent restart required"

# High: Significant functionality impact
severity="high" → "Primary service is down, falling back to secondary"
severity="high" → "Data processing pipeline has failed"

# Medium: Moderate impact with workarounds
severity="medium" → "Cache is unavailable, using slower direct queries"
severity="medium" → "Third-party API rate limit exceeded, queuing requests"

# Low: Minor issues or warnings
severity="low" → "Configuration file has deprecated settings"
severity="low" → "Performance is slightly degraded"
```

### 3. Rich Error Context

```python
# Good: Rich, structured context
context = {
    "agent_name": self.name,
    "agent_version": self.version,
    "operation": "data_validation",
    "error_code": "VALIDATION_001",
    "data_id": data.id,
    "data_type": type(data).__name__,
    "memory_usage": self.get_memory_usage(),
    "operation_duration": time.time() - start_time,
    "environment": os.getenv("AI_SYSTEM_ENV", "unknown"),
    "machine": socket.gethostname()
}
```

### 4. Error Throttling

```python
class ThrottledErrorReporter:
    def __init__(self, max_errors_per_minute=10):
        self.max_errors_per_minute = max_errors_per_minute
        self.error_counts = {}
        self.last_reset = time.time()
    
    def should_report_error(self, error_type):
        current_time = time.time()
        
        # Reset counters every minute
        if current_time - self.last_reset > 60:
            self.error_counts.clear()
            self.last_reset = current_time
        
        # Check if under limit
        count = self.error_counts.get(error_type, 0)
        if count < self.max_errors_per_minute:
            self.error_counts[error_type] = count + 1
            return True
        
        return False
```

## Troubleshooting

### Common Error Patterns

#### 1. Connection Errors

**Symptoms**: `connection_timeout`, `socket_error`, `network_unreachable`

**Solutions**:
- Verify network connectivity
- Check firewall rules
- Validate DNS resolution
- Increase timeout values
- Implement retry logic with exponential backoff

#### 2. Memory Errors

**Symptoms**: `out_of_memory`, `memory_leak`, `allocation_failure`

**Solutions**:
- Implement memory monitoring
- Add memory usage logging
- Use memory profiling tools
- Implement garbage collection strategies
- Set memory limits for components

#### 3. Performance Degradation

**Symptoms**: `high_cpu_usage`, `process_timeout`, `resource_exhaustion`

**Solutions**:
- Implement performance monitoring
- Profile slow operations
- Optimize algorithms and data structures
- Add caching layers
- Implement request throttling

#### 4. Data Corruption

**Symptoms**: `validation_error`, `parsing_error`, `consistency_violation`

**Solutions**:
- Implement data validation at boundaries
- Use checksums for data integrity
- Add data backup and recovery mechanisms
- Implement transaction logging
- Use schema validation

### Error Investigation Workflow

1. **Gather Error Context**: Collect comprehensive error information
2. **Analyze Error Patterns**: Look for similar errors in recent history
3. **Check System State**: Verify system health and resource usage
4. **Correlate Events**: Find related events and error sequences
5. **Apply Fixes**: Implement appropriate remediation strategies
6. **Monitor Results**: Verify error resolution and prevent recurrence

---

**Next**: See [configuration.md](configuration.md) for configuration management and [architecture.md](architecture.md) for system architecture overview.
