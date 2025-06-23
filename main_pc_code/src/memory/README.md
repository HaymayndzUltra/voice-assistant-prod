# Memory Module

This module provides memory storage, retrieval, and management services for the AI system.

## Components

### MemoryOrchestrator

The `MemoryOrchestrator` is the central service for memory management. It provides:

- Memory storage and retrieval
- Session management
- Memory search capabilities 
- Cross-machine memory distribution with PC2

### ZMQ Encoding Utilities

The `zmq_encoding_utils.py` module provides safe encoding and decoding functions for ZMQ communication. These utilities help prevent null byte issues and ensure reliable message transmission.

## Proper ZMQ Message Handling

When working with ZMQ in this project, follow these guidelines to avoid null byte issues:

### Do's:

1. **Use explicit encoding/decoding**:
   ```python
   # Sending a message
   message_json = json.dumps(message)
   socket.send(message_json.encode('utf-8'))
   
   # Receiving a message
   message_bytes = socket.recv()
   message_str = message_bytes.decode('utf-8')
   message = json.loads(message_str)
   ```

2. **Use the provided utilities**:
   ```python
   from main_pc_code.src.memory.zmq_encoding_utils import send_json_safe, recv_json_safe
   
   # Sending a message
   send_json_safe(socket, message)
   
   # Receiving a message
   message = recv_json_safe(socket)
   ```

3. **Handle encoding errors gracefully**:
   ```python
   try:
       message_str = message_bytes.decode('utf-8')
       message = json.loads(message_str)
   except UnicodeDecodeError:
       # Handle encoding error
   except json.JSONDecodeError:
       # Handle JSON error
   ```

### Don'ts:

1. **Don't use implicit methods without care**:
   ```python
   # Avoid these without proper error handling
   socket.send_json(message)  # Implicit encoding
   message = socket.recv_json()  # Implicit decoding
   ```

2. **Don't mix bytes and strings**:
   ```python
   # Avoid this kind of mixing
   socket.send(json.dumps(message))  # Missing encoding step
   message = json.loads(socket.recv())  # Missing decoding step
   ```

## Database Integration

The `MemoryOrchestrator` connects to a PostgreSQL database for persistent storage of memories. The database schema includes:

- `memory_entries`: Stores memory items
- `memory_tags`: Stores tags associated with memories
- `memory_access_log`: Tracks access to memories
- `sessions`: Manages user sessions

## Distributed Memory

The memory system integrates with PC2 through the `UnifiedMemoryReasoningAgent`. This enables:

1. Cross-machine memory sharing
2. Memory reinforcement and decay
3. Synchronized memory operations

## Recent Fixes

The module recently addressed null byte issues in ZMQ communication. See the detailed report at:
`/main_pc_code/_DOCUMENTSFINAL/implementation/memory_orchestrator_null_byte_fix.md` 