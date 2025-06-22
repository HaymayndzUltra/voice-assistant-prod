# Memory Orchestrator API

## Overview

The Memory Orchestrator provides a centralized interface for all memory operations across the voice assistant system. It unifies previously fragmented memory components, enabling consistent access to conversation history, contextual information, and user preferences.

## Service Endpoint

- **Socket Type:** ZMQ REP/REQ (Request-Reply pattern)
- **Port:** 5570
- **Base Address:** `tcp://localhost:5570`

## Message Format

All requests and responses use a standardized JSON format:

### Request Format

```json
{
  "action": "create|read|update|delete|batch_read|search",
  "session_id": "unique-session-identifier",
  "payload": { ... operation-specific data ... },
  "request_id": "unique-request-identifier",
  "timestamp": "2023-06-15T08:30:45.123Z"
}
```

### Response Format

```json
{
  "status": "success|error",
  "action": "create|read|update|delete|batch_read|search",
  "request_id": "matching-request-identifier",
  "data": { ... response data ... },
  "error": { ... error details if status is "error" ... },
  "timestamp": "2023-06-15T08:30:45.456Z"
}
```

## API Operations

### 1. Create Memory Entry

Creates a new memory entry in the database.

#### Request

```json
{
  "action": "create",
  "session_id": "session-123456",
  "payload": {
    "memory_type": "conversation|context|user_preference|agent_state",
    "content": {
      "text": "User asked about the weather in New York",
      "source_agent": "language_understanding_agent",
      "metadata": {
        "intent": "weather_query",
        "entities": ["New York"],
        "confidence": 0.95
      }
    },
    "tags": ["weather", "location", "query"],
    "ttl": 3600,
    "priority": 5
  },
  "request_id": "req-78901234",
  "timestamp": "2023-06-15T08:30:45.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "create",
  "request_id": "req-78901234",
  "data": {
    "memory_id": "mem-56789012",
    "created_at": "2023-06-15T08:30:45.456Z"
  },
  "timestamp": "2023-06-15T08:30:45.456Z"
}
```

### 2. Read Memory Entry

Retrieves a specific memory entry by ID.

#### Request

```json
{
  "action": "read",
  "session_id": "session-123456",
  "payload": {
    "memory_id": "mem-56789012"
  },
  "request_id": "req-89012345",
  "timestamp": "2023-06-15T08:31:00.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "read",
  "request_id": "req-89012345",
  "data": {
    "memory_id": "mem-56789012",
    "memory_type": "conversation",
    "content": {
      "text": "User asked about the weather in New York",
      "source_agent": "language_understanding_agent",
      "metadata": {
        "intent": "weather_query",
        "entities": ["New York"],
        "confidence": 0.95
      }
    },
    "tags": ["weather", "location", "query"],
    "created_at": "2023-06-15T08:30:45.456Z",
    "updated_at": "2023-06-15T08:30:45.456Z",
    "expires_at": "2023-06-15T09:30:45.456Z",
    "priority": 5
  },
  "timestamp": "2023-06-15T08:31:00.456Z"
}
```

### 3. Update Memory Entry

Updates an existing memory entry.

#### Request

```json
{
  "action": "update",
  "session_id": "session-123456",
  "payload": {
    "memory_id": "mem-56789012",
    "content": {
      "text": "User asked about the weather in New York City",
      "metadata": {
        "intent": "weather_query",
        "entities": ["New York City"],
        "confidence": 0.98
      }
    },
    "tags": ["weather", "location", "query", "city"],
    "ttl": 7200,
    "priority": 6
  },
  "request_id": "req-90123456",
  "timestamp": "2023-06-15T08:32:00.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "update",
  "request_id": "req-90123456",
  "data": {
    "memory_id": "mem-56789012",
    "updated_at": "2023-06-15T08:32:00.456Z",
    "expires_at": "2023-06-15T10:32:00.456Z"
  },
  "timestamp": "2023-06-15T08:32:00.456Z"
}
```

### 4. Delete Memory Entry

Deletes a specific memory entry or multiple entries.

#### Request

```json
{
  "action": "delete",
  "session_id": "session-123456",
  "payload": {
    "memory_id": "mem-56789012"
  },
  "request_id": "req-01234567",
  "timestamp": "2023-06-15T08:33:00.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "delete",
  "request_id": "req-01234567",
  "data": {
    "deleted": true
  },
  "timestamp": "2023-06-15T08:33:00.456Z"
}
```

### 5. Batch Read

Retrieves multiple memory entries in a single request.

#### Request

```json
{
  "action": "batch_read",
  "session_id": "session-123456",
  "payload": {
    "memory_ids": ["mem-56789012", "mem-67890123", "mem-78901234"],
    "filter": {
      "memory_type": "conversation",
      "time_range": {
        "start": "2023-06-15T08:00:00.000Z",
        "end": "2023-06-15T09:00:00.000Z"
      },
      "tags": ["weather"],
      "limit": 10,
      "offset": 0,
      "sort": {
        "field": "created_at",
        "order": "desc"
      }
    }
  },
  "request_id": "req-12345678",
  "timestamp": "2023-06-15T08:34:00.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "batch_read",
  "request_id": "req-12345678",
  "data": {
    "memories": [
      {
        "memory_id": "mem-56789012",
        "memory_type": "conversation",
        "content": {
          "text": "User asked about the weather in New York City",
          "source_agent": "language_understanding_agent",
          "metadata": {
            "intent": "weather_query",
            "entities": ["New York City"],
            "confidence": 0.98
          }
        },
        "tags": ["weather", "location", "query", "city"],
        "created_at": "2023-06-15T08:30:45.456Z",
        "updated_at": "2023-06-15T08:32:00.456Z",
        "expires_at": "2023-06-15T10:32:00.456Z",
        "priority": 6
      },
      {
        "memory_id": "mem-67890123",
        "memory_type": "conversation",
        "content": {
          "text": "Assistant provided weather information for New York City",
          "source_agent": "weather_agent",
          "metadata": {
            "temperature": "72°F",
            "conditions": "Partly Cloudy",
            "forecast": "Sunny later today"
          }
        },
        "tags": ["weather", "response"],
        "created_at": "2023-06-15T08:31:15.789Z",
        "updated_at": "2023-06-15T08:31:15.789Z",
        "expires_at": "2023-06-15T09:31:15.789Z",
        "priority": 5
      }
    ],
    "total_count": 2,
    "page_info": {
      "limit": 10,
      "offset": 0,
      "has_more": false
    }
  },
  "timestamp": "2023-06-15T08:34:00.456Z"
}
```

### 6. Contextual Search

Searches for memory entries based on semantic relevance to a query.

#### Request

```json
{
  "action": "search",
  "session_id": "session-123456",
  "payload": {
    "query": "weather forecast for new york",
    "search_type": "semantic|keyword|hybrid",
    "filters": {
      "memory_types": ["conversation", "context"],
      "time_range": {
        "start": "2023-06-14T00:00:00.000Z",
        "end": "2023-06-15T09:00:00.000Z"
      },
      "tags": ["weather"],
      "min_similarity": 0.7,
      "limit": 5
    }
  },
  "request_id": "req-23456789",
  "timestamp": "2023-06-15T08:35:00.123Z"
}
```

#### Response

```json
{
  "status": "success",
  "action": "search",
  "request_id": "req-23456789",
  "data": {
    "results": [
      {
        "memory_id": "mem-56789012",
        "memory_type": "conversation",
        "content": {
          "text": "User asked about the weather in New York City",
          "source_agent": "language_understanding_agent",
          "metadata": {
            "intent": "weather_query",
            "entities": ["New York City"],
            "confidence": 0.98
          }
        },
        "tags": ["weather", "location", "query", "city"],
        "created_at": "2023-06-15T08:30:45.456Z",
        "updated_at": "2023-06-15T08:32:00.456Z",
        "similarity_score": 0.92
      },
      {
        "memory_id": "mem-67890123",
        "memory_type": "conversation",
        "content": {
          "text": "Assistant provided weather information for New York City",
          "source_agent": "weather_agent",
          "metadata": {
            "temperature": "72°F",
            "conditions": "Partly Cloudy",
            "forecast": "Sunny later today"
          }
        },
        "tags": ["weather", "response"],
        "created_at": "2023-06-15T08:31:15.789Z",
        "updated_at": "2023-06-15T08:31:15.789Z",
        "similarity_score": 0.85
      }
    ],
    "total_count": 2,
    "search_metadata": {
      "search_type": "semantic",
      "embedding_model": "text-embedding-ada-002",
      "query_embedding_dimension": 1536
    }
  },
  "timestamp": "2023-06-15T08:35:00.456Z"
}
```

## Additional Endpoints

### Session Management

#### Create Session

```json
{
  "action": "create_session",
  "payload": {
    "user_id": "user-12345",
    "session_metadata": {
      "device_info": "MacOS Chrome Browser",
      "location": "Home Office",
      "session_type": "conversation"
    }
  },
  "request_id": "req-34567890",
  "timestamp": "2023-06-15T08:36:00.123Z"
}
```

#### End Session

```json
{
  "action": "end_session",
  "session_id": "session-123456",
  "payload": {
    "summary": "User asked about weather in New York and got forecast information",
    "archive": true
  },
  "request_id": "req-45678901",
  "timestamp": "2023-06-15T09:00:00.123Z"
}
```

### Memory Management

#### Bulk Delete

```json
{
  "action": "bulk_delete",
  "session_id": "session-123456",
  "payload": {
    "filter": {
      "memory_type": "conversation",
      "older_than": "2023-06-14T00:00:00.000Z",
      "tags": ["weather"]
    }
  },
  "request_id": "req-56789012",
  "timestamp": "2023-06-15T09:01:00.123Z"
}
```

#### Memory Summary

```json
{
  "action": "summarize",
  "session_id": "session-123456",
  "payload": {
    "memory_type": "conversation",
    "time_range": {
      "start": "2023-06-15T08:00:00.000Z",
      "end": "2023-06-15T09:00:00.000Z"
    }
  },
  "request_id": "req-67890123",
  "timestamp": "2023-06-15T09:02:00.123Z"
}
```

## Error Handling

### Error Response Format

```json
{
  "status": "error",
  "action": "create|read|update|delete|batch_read|search",
  "request_id": "matching-request-identifier",
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": { ... additional error context ... }
  },
  "timestamp": "2023-06-15T08:30:45.789Z"
}
```

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `invalid_request` | The request format is invalid or missing required fields |
| `memory_not_found` | The requested memory entry does not exist |
| `session_not_found` | The specified session does not exist |
| `permission_denied` | The requester does not have permission for this operation |
| `storage_error` | Error occurred while accessing the database |
| `search_error` | Error occurred during search operation |
| `validation_error` | The provided data failed validation |
| `rate_limit_exceeded` | Too many requests in a short time period |
| `internal_error` | An unexpected internal error occurred |

## Performance Considerations

1. **Caching:** Frequently accessed memories will be cached in-memory for faster retrieval
2. **Prioritization:** High-priority memory operations will be processed before lower priority ones
3. **Batching:** Batch operations should be used when possible to reduce network overhead
4. **Compression:** Large memory entries will be compressed for efficient storage
5. **Vector Optimization:** Semantic search vectors will be optimized for fast similarity calculations

## Security Considerations

1. **Authentication:** Memory Orchestrator will verify the identity of calling agents
2. **Authorization:** Access control checks will ensure agents can only access appropriate memories
3. **Encryption:** Sensitive memory content will be encrypted at rest
4. **Sanitization:** Input validation will protect against injection attacks
5. **Auditing:** All memory operations will be logged for security auditing

## PC2 Memory Services

- Unified Memory Reasoning Agent (port 5596)
- DreamWorld Agent (port 5598-PUB)
- Other PC2 memory services 