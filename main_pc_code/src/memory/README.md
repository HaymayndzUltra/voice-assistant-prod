# Memory Orchestrator Implementation

This directory contains the implementation of the Memory Orchestrator service and client library for the voice assistant system, following the specifications in the design documents.

## Overview

The Memory Orchestrator provides a centralized system for managing all memory operations across the voice assistant. It replaces the previously fragmented memory components with a unified API for storing, retrieving, and searching memories.

## Components

### 1. Memory Orchestrator Service (`memory_orchestrator.py`)

The main service that handles all memory operations. It:

- Listens for ZMQ REP/REQ messages on port 5570
- Provides handlers for all API operations defined in the design document
- Implements an in-memory LRU cache for fast retrieval of frequently accessed memories
- Contains placeholders for future database integration
- Supports all required operations: create, read, update, delete, batch read, search, etc.

### 2. Memory Client Library (`memory_client.py`)

A client library that other agents can use to interact with the Memory Orchestrator service. It:

- Provides a simple, Pythonic interface for all Memory Orchestrator operations
- Handles request formatting and error handling
- Supports session management
- Includes logging and diagnostics

## Implementation Notes

1. **Caching**: The implementation includes a full LRU (Least Recently Used) cache with time-based expiration to improve performance.

2. **Database Integration**: The code includes placeholders (marked with comments like `# DB_WRITE_LOGIC_HERE`) where database integration will be added in a future phase.

3. **Error Handling**: Comprehensive error handling is implemented, with appropriate error codes and messages returned to clients.

4. **ID Generation**: Unique IDs are generated for memories and sessions using a prefix and a random component.

5. **Session Management**: Full session lifecycle management is supported, including creation, updates, and ending sessions.

## Usage Example

```python
from src.memory.memory_client import MemoryClient

# Create a client and start a session
client = MemoryClient()
session_response = client.create_session(
    session_metadata={
        "device_info": "Windows PC",
        "location": "Home"
    }
)

# Create a memory entry
memory_response = client.create_memory(
    memory_type="conversation",
    content={
        "text": "User asked about the weather",
        "source_agent": "language_understanding_agent"
    },
    tags=["weather", "query"]
)

# Retrieve a memory entry
memory_id = memory_response["data"]["memory_id"]
get_response = client.get_memory(memory_id)

# Search for memories
search_response = client.search(
    query="weather",
    memory_types=["conversation"],
    tags=["weather"]
)
```

## Future Enhancements

1. **Database Integration**: Implement the PostgreSQL database backend as specified in `memory_db_schema.md`.

2. **Vector Search**: Add vector embeddings for efficient semantic search capabilities.

3. **Authentication**: Add authentication mechanisms for secure access.

4. **Compression**: Implement compression for large memory entries.

5. **Monitoring**: Add performance metrics and monitoring capabilities.
