# Utility CPU & Translation Group - Container Status Report
**Report Generated:** 2025-08-02 16:17:30

## Group Overview
- **Total Containers:** 8
- **Healthy:** 6
- **Unhealthy:** 1
- **Stopped:** 1

## ✅ HEALTHY CONTAINERS

### redis_translation
- **Status:** Up 9 hours (healthy)
- **Ports:** 0.0.0.0:6384->6379/tcp
- **Issue:** None - Working correctly

### nats_translation
- **Status:** Up 9 hours (healthy)
- **Ports:** 0.0.0.0:4226->4222/tcp
- **Issue:** None - Working correctly

### redis_utility
- **Status:** Up 10 hours (healthy)
- **Ports:** 0.0.0.0:6382->6379/tcp
- **Issue:** None - Working correctly

### fixed_streaming_translation
- **Status:** Up 12 seconds (healthy)
- **Ports:** 0.0.0.0:5584->5584/tcp, 0.0.0.0:6584->6584/tcp
- **Issue:** None - Working correctly

### code_generator
- **Status:** Up 10 hours (healthy)
- **Issue:** None - Working correctly

### nllb_adapter
- **Status:** Up 9 hours
- **Ports:** 0.0.0.0:5582->5582/tcp, 0.0.0.0:6582->6582/tcp
- **Issue:** None - Working correctly

### executor
- **Status:** Up 16 seconds
- **Issue:** None - Working correctly

## ⚠️ UNHEALTHY CONTAINERS

### service_registry
- **Status:** Up 13 hours (unhealthy)
- **Ports:** 0.0.0.0:7200->7200/tcp, 0.0.0.0:8200->8200/tcp
- **Issue:** NATS connectivity failure + SystemDigitalTwin communication issues

**Logs:**
```
NATS Error: Multiple exceptions: [Errno 111] Connect call failed ('::1', 4222, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 4222)
Timeout waiting for response from SystemDigitalTwin (attempt 1/3)
[multiple NATS connection failures]
Failed to register with SystemDigitalTwin: Failed to communicate with SystemDigitalTwin after 3 attempts. Will continue without registration.
❌ Failed to connect to NATS: nats: no servers available for connection
⚠️ NATS error bus initialization failed for ServiceRegistry: nats: no servers available for connection
```

## ❌ STOPPED CONTAINERS

### translation_service_fixed
- **Status:** Exited (0) 8 minutes ago
- **Issue:** ZMQ port conflict (hardcoded port 5595)
- **Error:** `zmq.error.ZMQError: Address already in use (addr='tcp://*:5595')`

**Logs:**
```
File "/app/common/pools/zmq_pool.py", line 125, in _create_socket
    socket.bind(config.endpoint)
zmq.error.ZMQError: Address already in use (addr='tcp://*:5595')
An unexpected error occurred in agent: Address already in use (addr='tcp://*:5595')
```

## Root Cause Analysis

### ZMQ Port Conflicts
- **translation_service_fixed** trying to bind to hardcoded port 5595
- Port already in use by another service
- ZMQ socket binding not respecting environment variables

### NATS Connectivity Issues
- **service_registry** can't connect to NATS on localhost:4222
- NATS server may be running on different network or port
- Docker networking configuration issue

### SystemDigitalTwin Communication
- Multiple agents failing to register with SystemDigitalTwin
- Cross-group communication issues

## Required Fixes

### For translation_service_fixed:
1. Update agent code to use AGENT_PORT environment variable instead of hardcoded 5595
2. Check zmq_pool.py configuration to respect dynamic port assignment
3. Restart container with proper port configuration

### For service_registry:
1. Fix NATS connection string to use correct Docker network addresses
2. Ensure infra_core NATS container is accessible
3. Update NATS_SERVERS environment variable

### For SystemDigitalTwin Communication:
1. Verify system_digital_twin container is accessible
2. Check cross-group Docker networking configuration
3. Update service discovery mechanisms

## Summary
Utility CPU & Translation group is 75% functional. Main issues are port conflicts and cross-service communication. Infrastructure services are healthy.
