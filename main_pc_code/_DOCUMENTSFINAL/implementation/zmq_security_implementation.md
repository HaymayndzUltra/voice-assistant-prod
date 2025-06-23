# ZMQ Security Implementation Summary

This document provides an overview of the ZMQ security implementation in the AI System.

## Overview

The system utilizes ZMQ's CURVE security mechanism to enable secure communication between agents running on different machines (MainPC and PC2). This security layer uses public-key cryptography to:

1. Authenticate clients and servers
2. Ensure the confidentiality and integrity of communications

## Implementation Components

### 1. Secure ZMQ Module

**File:** `/main_pc_code/src/network/secure_zmq.py`

This module provides the core security functionality:

- **ZMQAuthenticator** - A singleton class that manages the ZMQ authentication thread
- **Certificate Management** - Functions to load CURVE certificates
- **Socket Security** - Functions to configure sockets with CURVE security:
  - `secure_server_socket()` - For server sockets
  - `secure_client_socket()` - For client sockets
  - Compatibility aliases: `configure_secure_server()` and `configure_secure_client()`

### 2. Certificate Generation

**File:** `/scripts/generate_zmq_certificates.py`

This script generates the CURVE certificates needed for secure communication:
- Server key pair (server.key and server.key_secret)
- Client key pair (client.key and client.key_secret)

### 3. Network Configuration

**File:** `/config/network_config.yaml`

This centralized configuration file stores the IP addresses of MainPC and PC2, used to establish connections between agents.

**File:** `/main_pc_code/utils/network_utils.py`

This utility module provides functions to:
- Load the network configuration
- Retrieve server addresses with helper methods like `get_mainpc_address()` and `get_pc2_address()`

## Integration

### Enabling Security

Security is controlled via the `SECURE_ZMQ` environment variable:

```bash
# Enable security
export SECURE_ZMQ=1

# Disable security
export SECURE_ZMQ=0
```

### Server Implementation (SystemDigitalTwin)

The server checks for the `SECURE_ZMQ` environment variable and configures security accordingly:

```python
secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
if secure_zmq:
    from main_pc_code.src.network.secure_zmq import configure_secure_server
    self.socket = configure_secure_server(self.socket)
```

### Client Implementation (UnifiedMemoryReasoningAgent)

The client similarly checks for the environment variable and configures security:

```python
self.use_secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
if self.use_secure_zmq:
    from main_pc_code.src.network.secure_zmq import secure_client_socket
    self.socket = secure_client_socket(self.socket)
```

## Cross-Machine Communication Flow

1. The `SystemDigitalTwin` agent runs on MainPC and binds to its configured port with security enabled
2. The `UnifiedMemoryReasoningAgent` on PC2 loads the network configuration to find MainPC's IP address
3. The agent connects to `SystemDigitalTwin` using the secure ZMQ connection
4. Both sides authenticate using their CURVE certificates
5. Communications are now encrypted and secure

## Testing

Testing is handled by several scripts:

1. `scripts/secure_sdt_client.py` - A simplified client for testing connections to SystemDigitalTwin
2. `scripts/test_sdt_security.py` - Tests SystemDigitalTwin's security implementation
3. `scripts/test_unified_memory_agent.py` - Tests the UnifiedMemoryReasoningAgent's connection to SystemDigitalTwin

## Security Features

- **Authentication** - Clients and servers authenticate each other using their certificates
- **Encryption** - All communications are encrypted using the CURVE keys
- **Replay Protection** - ZMQ's CURVE mechanism includes protection against replay attacks
- **Message Integrity** - Messages cannot be tampered with during transmission

## Deployment Requirements

1. The certificates directory (`/certificates`) must be synced between MainPC and PC2
2. The `SECURE_ZMQ` environment variable must be set consistently on both machines
3. The network configuration (`/config/network_config.yaml`) must contain the correct IP addresses

## Best Practices

1. Keep certificate secret keys (`*.key_secret`) secure and with restrictive file permissions
2. Regenerate certificates periodically for enhanced security
3. Always test secure connections in a controlled environment before deployment 