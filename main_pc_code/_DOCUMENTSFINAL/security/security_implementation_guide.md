# ZMQ CURVE Security Implementation Guide

## Overview

This guide outlines the steps taken to secure the Voice Assistant system's ZMQ communication using the CURVE security mechanism. CURVE provides strong encryption and authentication for all ZMQ sockets, preventing unauthorized access and ensuring data confidentiality.

## Components Implemented

### 1. Certificate Generation

- Created `tools/generate_certificates.py` to generate CURVE certificates
- The script generates:
  - `server.key_secret` and `server.key` for server sockets
  - `client.key_secret` and `client.key` for client sockets
- All certificates are stored in the `certificates` directory at the project root

### 2. Secure ZMQ Module

- Implemented `src/network/secure_zmq.py` with helper functions:
  - `secure_server_socket()`: Configures a socket as a secure server
  - `secure_client_socket()`: Configures a socket as a secure client
  - `start_auth()`: Starts the ZMQ authenticator thread
  - `stop_auth()`: Stops the ZMQ authenticator thread
  - `create_secure_context()`: Creates a ZMQ context with security enabled

### 3. Secure Agent Template

- Created `src/core/secure_agent_template.py` as a reference implementation
- Demonstrates how to:
  - Initialize secure ZMQ contexts
  - Create secure server and client sockets
  - Handle authentication properly

### 4. Docker Integration

- Updated all Dockerfiles to include `libsodium-dev` for CURVE support
- Added a security setup service in `docker-compose.yaml` to generate certificates
- Added certificate volume mounts to all services
- Added `SECURE_ZMQ=1` environment variable to enable security

### 5. Dependencies

- Updated `requirements.txt` to include `pyzmq[libsodium]` for CURVE support

## How to Secure an Agent

To secure an existing agent, follow these steps:

1. **Import the Secure ZMQ Module**

```python
from src.network.secure_zmq import (
    secure_server_socket,
    secure_client_socket,
    start_auth,
    stop_auth,
    create_secure_context
)
```

2. **Initialize the ZMQ Context Securely**

```python
# Check if security is enabled
use_secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"

# Initialize context
if use_secure_zmq:
    context = create_secure_context()
else:
    context = zmq.Context()
```

3. **Secure Server Sockets (REP, PUB)**

```python
socket = context.socket(zmq.REP)
if use_secure_zmq:
    socket = secure_server_socket(socket)
socket.bind("tcp://*:5555")
```

4. **Secure Client Sockets (REQ, SUB)**

```python
socket = context.socket(zmq.REQ)
if use_secure_zmq:
    socket = secure_client_socket(socket)
socket.connect("tcp://localhost:5555")
```

5. **Start the Authenticator**

```python
if use_secure_zmq:
    start_auth()
```

6. **Stop the Authenticator When Done**

```python
if use_secure_zmq:
    stop_auth()
```

## Security Implementation Checklist

- [x] Generate CURVE certificates
- [x] Create secure ZMQ helper module
- [x] Create secure agent template
- [x] Update dependencies to include libsodium
- [x] Update Docker configuration
- [x] Document the implementation process

## Testing Secure Communication

To test secure communication between agents:

1. Generate certificates:
   ```bash
   python tools/generate_certificates.py
   ```

2. Run a secure server:
   ```bash
   SECURE_ZMQ=1 python src/core/secure_agent_template.py --mode server
   ```

3. Run a secure client:
   ```bash
   SECURE_ZMQ=1 python src/core/secure_agent_template.py --mode client
   ```

4. Verify that communication is successful and encrypted

## Security Benefits

- **Authentication**: Only authorized clients can connect to servers
- **Encryption**: All data is encrypted during transmission
- **Integrity**: Messages cannot be tampered with
- **Non-repudiation**: Clients cannot deny sending messages
- **Forward Secrecy**: Past communications remain secure even if keys are compromised

## Next Steps

1. **Key Rotation**: Implement a process for regular certificate rotation
2. **Access Control**: Add more granular access control based on client identities
3. **Monitoring**: Add security event monitoring and logging
4. **Penetration Testing**: Conduct security testing to verify the implementation 