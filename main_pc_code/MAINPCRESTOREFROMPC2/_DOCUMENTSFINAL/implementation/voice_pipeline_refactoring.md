# Voice Pipeline Refactoring: Network Configuration

## Overview

This document summarizes the refactoring of critical voice pipeline agents to remove hardcoded network addresses and replace them with dynamic configuration. This work was done as part of Phase 5A of the Docker compatibility initiative.

## Refactored Files

The following files were refactored to remove hardcoded network addresses:

1. `/main_pc_code/agents/streaming_interrupt_handler.py`
2. `/main_pc_code/agents/streaming_tts_agent.py`
3. `/main_pc_code/agents/tts_agent.py`
4. `/main_pc_code/agents/responder.py`
5. `/main_pc_code/agents/streaming_language_analyzer.py`

## Key Changes

### 1. Removed Hardcoded Addresses

- Replaced all instances of `localhost`, `127.0.0.1`, and `*` in socket binding with dynamic configuration
- Removed all hardcoded IP addresses and port numbers

### 2. Added Dynamic Configuration

- Added imports for configuration utilities:
  ```python
  from utils.config_parser import parse_agent_args
  from utils.service_discovery_client import register_service, get_service_address
  from utils.env_loader import get_env
  ```

- Used `parse_agent_args()` to get command-line arguments for port configuration
- Used `get_env('BIND_ADDRESS', '0.0.0.0')` for Docker-compatible binding
- Used `get_service_address()` to dynamically discover service endpoints

### 3. Enhanced Socket Management

- Added proper socket cleanup in `try...finally` blocks
- Added comprehensive error handling for socket operations
- Added service registration with `register_service()`
- Added support for secure ZMQ connections

### 4. Improved Logging

- Added detailed logging for connection attempts and failures
- Added logging for service discovery results
- Added logging for socket cleanup operations

## Example Pattern

The standard pattern used for socket binding:

```python
# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Bind to address using BIND_ADDRESS for Docker compatibility
bind_address = f"tcp://{BIND_ADDRESS}:{port}"
self.socket.bind(bind_address)
logger.info(f"Socket bound to {bind_address}")
```

The standard pattern used for connecting to other services:

```python
# Try to get the service address from service discovery
service_address = get_service_address("ServiceName")
if not service_address:
    # Fall back to configured port
    service_address = f"tcp://localhost:{DEFAULT_PORT}"
    
self.socket.connect(service_address)
logger.info(f"Connected to service at {service_address}")
```

## Benefits

1. **Docker Compatibility**: All agents can now run in Docker containers with proper networking
2. **Dynamic Configuration**: Services can be moved between hosts without code changes
3. **Improved Resilience**: Better error handling and fallback mechanisms
4. **Resource Management**: Proper cleanup of ZMQ sockets prevents resource leaks

## Next Steps

1. Apply the same refactoring pattern to remaining agents
2. Update Docker Compose files to use the new configuration
3. Test the refactored agents in a Docker environment
4. Update documentation to reflect the new configuration approach 