# Cross-System Communication Protocols
## MainPC ↔ PC2 Integration

**Version**: 1.0  
**Created**: 2025-07-30  
**Purpose**: Define communication protocols, APIs, and integration patterns between MainPC and PC2 systems

---

## 1. Architecture Overview

### 1.1 Communication Topology

```
┌─────────────────────────┐         ┌─────────────────────────┐
│      MainPC (RTX 4090)  │         │      PC2 (RTX 3060)     │
├─────────────────────────┤         ├─────────────────────────┤
│                         │         │                         │
│  ┌─────────────────┐   │  ZMQ    │  ┌─────────────────┐   │
│  │ ModelManager    │◄──┼─────────┼──│ Inference Client│   │
│  │ Suite           │   │  :7211   │  │                 │   │
│  └─────────────────┘   │         │  └─────────────────┘   │
│                         │         │                         │
│  ┌─────────────────┐   │  HTTP   │  ┌─────────────────┐   │
│  │ ObservabilityHub│◄──┼─────────┼──│ ObservabilityHub│   │
│  │                 │   │  :9000   │  │ PC2             │   │
│  └─────────────────┘   │         │  └─────────────────┘   │
│                         │         │                         │
│  ┌─────────────────┐   │  Redis  │  ┌─────────────────┐   │
│  │ SystemDigital   │◄──┼─────────┼──│ MemoryOrchest   │   │
│  │ Twin            │   │  Cluster │  │ rator           │   │
│  └─────────────────┘   │         │  └─────────────────┘   │
└─────────────────────────┘         └─────────────────────────┘
```

### 1.2 Communication Channels

1. **ZMQ (ZeroMQ)** - High-performance async messaging for AI inference
2. **HTTP/REST** - Standard API calls for monitoring and control
3. **Redis Pub/Sub** - Event streaming and shared state
4. **gRPC** - Future option for typed service calls

---

## 2. Protocol Specifications

### 2.1 AI Inference Protocol (ZMQ)

#### Request Format
```python
{
    "id": "uuid-v4",
    "timestamp": "2025-07-30T12:00:00Z",
    "source": {
        "system": "pc2",
        "agent": "UnifiedMemoryReasoningAgent",
        "instance_id": "pc2-001"
    },
    "request": {
        "type": "inference",
        "model": "phi-3-mini-128k-instruct",
        "method": "generate",
        "params": {
            "prompt": "Analyze the following memory pattern...",
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9
        },
        "priority": "normal",  # low, normal, high, critical
        "timeout_ms": 30000
    },
    "auth": {
        "token": "jwt-token-here",
        "signature": "hmac-sha256-signature"
    }
}
```

#### Response Format
```python
{
    "id": "uuid-v4",
    "request_id": "original-request-id",
    "timestamp": "2025-07-30T12:00:01Z",
    "status": "success",  # success, error, timeout, degraded
    "response": {
        "model_used": "phi-3-mini-128k-instruct",
        "inference_time_ms": 523,
        "result": {
            "text": "Based on the memory pattern analysis...",
            "tokens_generated": 256,
            "finish_reason": "stop"
        },
        "metadata": {
            "gpu_memory_used_mb": 2048,
            "queue_time_ms": 15,
            "fallback_used": false
        }
    },
    "error": null
}
```

#### Error Response
```python
{
    "id": "uuid-v4",
    "request_id": "original-request-id",
    "status": "error",
    "error": {
        "code": "MODEL_OVERLOADED",
        "message": "Model queue is full, please retry",
        "retry_after_ms": 5000,
        "fallback_available": true
    }
}
```

### 2.2 Monitoring Protocol (HTTP/REST)

#### Health Check Endpoint
```
GET http://mainpc:9000/api/v1/health/cross-system
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2025-07-30T12:00:00Z",
    "systems": {
        "mainpc": {
            "status": "healthy",
            "agents_active": 45,
            "agents_healthy": 44,
            "resource_usage": {
                "cpu_percent": 45.2,
                "memory_gb": 32.5,
                "gpu_memory_gb": 18.2
            }
        },
        "pc2": {
            "status": "healthy",
            "agents_active": 23,
            "agents_healthy": 23,
            "last_sync": "2025-07-30T11:59:55Z",
            "latency_ms": 12
        }
    }
}
```

#### Metrics Sync
```
POST http://mainpc:9000/api/v1/metrics/sync
Content-Type: application/json

{
    "source": "pc2",
    "timestamp": "2025-07-30T12:00:00Z",
    "metrics": [
        {
            "name": "agent_request_count",
            "value": 1523,
            "labels": {
                "agent": "DreamWorldAgent",
                "status": "success"
            }
        },
        // ... more metrics
    ]
}
```

### 2.3 Event Streaming Protocol (Redis Pub/Sub)

#### Channel Structure
```
cascade:events:mainpc    # Events from MainPC
cascade:events:pc2       # Events from PC2
cascade:events:global    # System-wide events
cascade:state:agents     # Agent state updates
cascade:commands:*       # Command channels
```

#### Event Format
```json
{
    "event_id": "uuid-v4",
    "timestamp": "2025-07-30T12:00:00Z",
    "source": {
        "system": "mainpc",
        "agent": "ModelManagerSuite",
        "instance": "mainpc-prod-001"
    },
    "event": {
        "type": "model_loaded",
        "severity": "info",
        "data": {
            "model": "whisper-large-v3",
            "load_time_ms": 4523,
            "memory_allocated_mb": 3072
        }
    }
}
```

---

## 3. Authentication & Security

### 3.1 JWT Token Structure

```json
{
    "header": {
        "alg": "RS256",
        "typ": "JWT"
    },
    "payload": {
        "iss": "cascade-auth",
        "sub": "pc2-system",
        "aud": ["mainpc-inference", "mainpc-monitoring"],
        "exp": 1690804800,
        "iat": 1690718400,
        "jti": "unique-token-id",
        "permissions": [
            "inference:request",
            "metrics:write",
            "events:publish"
        ]
    }
}
```

### 3.2 TLS Configuration

```yaml
tls:
  enabled: true
  version: "1.3"
  certificates:
    ca: /certs/cascade-ca.crt
    cert: /certs/system.crt
    key: /certs/system.key
  cipher_suites:
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
  verify_client: true
```

### 3.3 API Key Management

```python
# API key structure
api_key = {
    "key_id": "pc2-prod-001",
    "secret": "base64-encoded-secret",
    "created": "2025-07-30T00:00:00Z",
    "expires": "2026-07-30T00:00:00Z",
    "scopes": ["inference", "monitoring"],
    "rate_limits": {
        "requests_per_minute": 1000,
        "burst": 100
    }
}
```

---

## 4. Message Queue Integration

### 4.1 Queue Configuration

```yaml
message_queues:
  inference_queue:
    type: zmq_router_dealer
    frontend_port: 7211
    backend_port: 7212
    high_water_mark: 1000
    timeout_ms: 30000
    
  event_queue:
    type: redis_stream
    max_length: 10000
    consumer_groups:
      - monitoring
      - persistence
      - analytics
```

### 4.2 Priority Queue Implementation

```python
class PriorityQueue:
    PRIORITIES = {
        'critical': 0,  # Highest priority
        'high': 1,
        'normal': 2,
        'low': 3
    }
    
    def enqueue(self, message):
        priority = self.PRIORITIES.get(
            message.get('request', {}).get('priority', 'normal'),
            2
        )
        timestamp = time.time()
        self.queue.put((priority, timestamp, message))
```

---

## 5. Failover & Resilience

### 5.1 Circuit Breaker Pattern

```python
circuit_breaker_config = {
    "failure_threshold": 5,
    "success_threshold": 2,
    "timeout": 60,  # seconds
    "half_open_requests": 3,
    "exclude_errors": ["RATE_LIMITED", "AUTH_FAILED"]
}
```

### 5.2 Retry Strategy

```python
retry_config = {
    "max_attempts": 3,
    "base_delay_ms": 1000,
    "max_delay_ms": 30000,
    "exponential_base": 2,
    "jitter": True,
    "retry_on": [
        "CONNECTION_ERROR",
        "TIMEOUT",
        "SERVICE_UNAVAILABLE"
    ]
}
```

### 5.3 Fallback Mechanisms

```yaml
fallbacks:
  inference:
    primary: mainpc_model_manager
    secondary: cloud_api_openai
    conditions:
      - error_rate > 0.1
      - latency_p99 > 5000
      - circuit_breaker_open
```

---

## 6. Performance Optimization

### 6.1 Connection Pooling

```python
connection_pool_config = {
    "min_connections": 5,
    "max_connections": 50,
    "connection_timeout_ms": 5000,
    "idle_timeout_ms": 300000,
    "validation_interval_ms": 30000,
    "eviction_strategy": "LRU"
}
```

### 6.2 Message Compression

```yaml
compression:
  enabled: true
  algorithm: lz4  # Options: lz4, zstd, gzip
  level: 3
  min_size_bytes: 1024
  exclude_types:
    - health_check
    - ping
```

### 6.3 Batching Configuration

```python
batch_config = {
    "max_batch_size": 32,
    "max_wait_ms": 100,
    "adaptive_batching": True,
    "optimization_interval_ms": 60000
}
```

---

## 7. Monitoring & Observability

### 7.1 Metrics to Track

```yaml
cross_system_metrics:
  - name: cross_system_latency_ms
    type: histogram
    labels: [source, destination, operation]
    
  - name: message_queue_depth
    type: gauge
    labels: [queue_name, priority]
    
  - name: inference_requests_total
    type: counter
    labels: [source, model, status]
    
  - name: bandwidth_bytes_per_second
    type: gauge
    labels: [direction, protocol]
```

### 7.2 Distributed Tracing

```python
# Trace context propagation
trace_headers = {
    "X-Trace-ID": "unique-trace-id",
    "X-Span-ID": "unique-span-id",
    "X-Parent-Span-ID": "parent-span-id",
    "X-Sampling-Priority": "1"
}
```

### 7.3 Alert Rules

```yaml
alerts:
  - name: HighCrossSystemLatency
    expr: histogram_quantile(0.99, cross_system_latency_ms) > 1000
    for: 5m
    severity: warning
    
  - name: InferenceQueueBacklog
    expr: message_queue_depth{queue_name="inference"} > 100
    for: 2m
    severity: critical
```

---

## 8. Development Guidelines

### 8.1 Client Library Usage

```python
from cascade.cross_system import CrossSystemClient

# Initialize client
client = CrossSystemClient(
    system_id="pc2",
    mainpc_endpoint="tcp://mainpc:7211",
    auth_token=os.environ["CASCADE_AUTH_TOKEN"]
)

# Make inference request
async def get_inference():
    response = await client.inference.generate(
        model="phi-3-mini",
        prompt="Analyze this pattern",
        max_tokens=1024,
        timeout_ms=30000
    )
    return response.result
```

### 8.2 Error Handling Best Practices

```python
try:
    result = await client.request_inference(payload)
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Use fallback or queue for retry
except TimeoutError as e:
    logger.warning(f"Request timeout: {e}")
    # Return cached result if available
except AuthenticationError as e:
    logger.error(f"Auth failed: {e}")
    # Refresh token and retry
except ModelOverloadedError as e:
    logger.info(f"Model busy: {e}")
    # Use cloud fallback
```

### 8.3 Testing Cross-System Communication

```bash
# Unit tests for protocol compliance
pytest tests/cross_system/test_protocols.py

# Integration tests with mock systems
docker-compose -f tests/docker-compose.test.yml up
pytest tests/cross_system/test_integration.py

# Load testing
locust -f tests/cross_system/loadtest.py \
  --host=http://mainpc:9000 \
  --users=100 \
  --spawn-rate=10
```

---

## 9. Deployment Considerations

### 9.1 Network Requirements

- **Bandwidth**: Minimum 1Gbps between systems
- **Latency**: < 10ms for real-time operations
- **Packet Loss**: < 0.1% for stable operation
- **MTU**: 9000 (jumbo frames) recommended

### 9.2 Firewall Rules

```bash
# MainPC ingress rules
ufw allow from 172.21.0.0/16 to any port 7211 proto tcp  # Inference
ufw allow from 172.21.0.0/16 to any port 9000 proto tcp  # Monitoring
ufw allow from 172.21.0.0/16 to any port 6379 proto tcp  # Redis

# PC2 ingress rules  
ufw allow from 172.20.0.0/16 to any port 9100 proto tcp  # Monitoring
```

### 9.3 DNS Configuration

```
# /etc/hosts or DNS server
172.20.1.10  mainpc mainpc.cascade.local
172.21.1.10  pc2 pc2.cascade.local
```

---

## 10. Troubleshooting Guide

### 10.1 Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Connection Refused | ZMQ ECONNREFUSED | Check firewall, verify service is running |
| Auth Failures | 401/403 responses | Verify token expiry, check scopes |
| High Latency | >100ms response times | Check network, enable compression |
| Message Loss | Missing events | Increase queue sizes, check memory |

### 10.2 Debug Tools

```bash
# Test connectivity
nc -zv mainpc 7211

# Monitor ZMQ traffic
sudo tcpdump -i any -n port 7211

# Check Redis connectivity
redis-cli -h mainpc ping

# View message queue stats
curl http://mainpc:9001/api/v1/queues/stats
```

### 10.3 Performance Tuning

```bash
# Increase socket buffers
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# TCP optimization
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.ipv4.tcp_fastopen=3
```

---

## Appendix A: Message Type Reference

| Message Type | Protocol | Direction | Description |
|--------------|----------|-----------|-------------|
| inference_request | ZMQ | PC2→MainPC | AI model inference |
| inference_response | ZMQ | MainPC→PC2 | Inference results |
| health_check | HTTP | Bidirectional | System health |
| metrics_sync | HTTP | PC2→MainPC | Metrics aggregation |
| event_stream | Redis | Bidirectional | Real-time events |
| state_sync | Redis | Bidirectional | Agent state updates |

## Appendix B: Error Codes

| Code | Name | Description | Retry |
|------|------|-------------|-------|
| 1001 | CONNECTION_ERROR | Network connection failed | Yes |
| 1002 | TIMEOUT | Request exceeded timeout | Yes |
| 2001 | AUTH_FAILED | Authentication failed | No |
| 2002 | PERMISSION_DENIED | Insufficient permissions | No |
| 3001 | MODEL_NOT_FOUND | Requested model unavailable | No |
| 3002 | MODEL_OVERLOADED | Model queue full | Yes |
| 4001 | INVALID_REQUEST | Malformed request | No |
| 5001 | INTERNAL_ERROR | Server error | Yes |